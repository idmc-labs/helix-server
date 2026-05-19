from __future__ import annotations

import abc
import cgi
import contextlib
import json
import logging
import mimetypes
import typing
import uuid
from pathlib import Path
from urllib.parse import unquote

import httpx
import pydantic
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone

from apps.contrib.bulk_operations.tasks import InternalHelixGraphQlClient
from apps.hulk.models import (
    HulkAttachment,
    HulkBulkImport,
    HulkEntityRelationBase,
    HulkEntry,
    HulkEvent,
    HulkFigure,
    HulkSourcePreview,
)
from apps.users.models import User

from .models import (
    HulkAttachmentImport,
    HulkBaseModel,
    HulkEntryImport,
    HulkEventImport,
    HulkFigureImport,
    HulkSourcePreviewImport,
)
from .utils import parse_aws_s3_url, parse_same_storage_url

logger = logging.getLogger(__name__)

PRE_ERROR_KEY = "pre-errors"
POST_ERROR_KEY = "post-errors"


class _InputBuildError(Exception):
    """Raised by ``_build_mutation_input`` overrides when input prep fails.

    The handler catches this and records the message as a ``post-errors``
    entry on the row, since the failure happened after pydantic validation
    but before the GraphQL mutation could run.
    """


class _CreateEntityError(Exception):
    """
    Raised by ``_create_entity`` to abort entity creation with a structured
    post-error payload (a dict / list / str — whatever helps the operator
    debug). ``handle_row`` catches it and writes a ``post-errors`` row.
    """

    def __init__(self, payload):
        super().__init__(str(payload))
        self.payload = payload


class _PreCheckError(Exception):
    """
    Raised before any entity-creation work to fail a row with a pre-error.
    Used e.g. when an attachment ``file_url`` points at an AWS S3 bucket that
    is not on the ``HULK_TRUSTED_SOURCE_BUCKETS`` allowlist — we refuse the
    row instead of degrading to a bytes-through-httpx download.
    """


class JsonlParseError(typing.NamedTuple):
    """
    Sentinel yielded by :func:`iter_jsonl_field` for lines that can't be
    decoded as UTF-8 or parsed as JSON. The process loop catches these and
    records a row-level pre-error so one bad line doesn't abort the import.
    """

    line_no: int
    message: str


def iter_jsonl_field(field_file) -> typing.Optional[typing.Generator]:
    """
    Stream JSONL rows out of a Django FieldFile. Returns None when the field is
    empty (so callers can short-circuit per-resource without opening anything).

    Yields ``dict`` for valid rows and :class:`JsonlParseError` for malformed
    lines — callers MUST check the type before treating the value as a row.
    """
    if not field_file:
        return None

    def _gen():
        try:
            with field_file.open("rb") as raw:
                for line_no, raw_line in enumerate(raw, start=1):
                    try:
                        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                    except UnicodeDecodeError as e:
                        yield JsonlParseError(line_no=line_no, message=f"utf-8 decode error: {e}")
                        continue
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError as e:
                        yield JsonlParseError(line_no=line_no, message=f"invalid json: {e}")
        finally:
            field_file.close()

    return _gen()


def _jsonl_default(o):
    if isinstance(o, uuid.UUID):
        return str(o)
    if isinstance(o, set):
        return list(o)
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


def dump_jsonl(rows: typing.Iterable[dict]) -> bytes:
    return ("\n".join(json.dumps(r, default=_jsonl_default) for r in rows) + "\n").encode("utf-8")


def get_filename_from_response(response, fallback="attachment"):
    # Try Content-Disposition
    cd = response.headers.get("content-disposition")
    if cd:
        _, params = cgi.parse_header(cd)

        # RFC 5987 (filename*=UTF-8''...)
        if "filename*" in params:
            return unquote(params["filename*"].split("''")[-1])

        # Standard filename=
        if "filename" in params:
            return params["filename"]

    # Try MIME type → extension
    content_type = response.headers.get("content-type")
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0])
        if ext:
            return f"{fallback}{ext}"

    # Final fallback
    return fallback


def download_file(url):
    """
    Fetch a file via HTTP for the attachment handler's slow path.

    Note: same-bucket / same-MinIO and AWS S3 URLs are handled server-side via
    ``s3.copy_object`` in ``HulkHelixAttachmentImportHandler``, so this should
    only be reached for true external URLs.
    """
    response = httpx.get(url)

    filename = get_filename_from_response(response, fallback="attachment")

    return ContentFile(
        response.content,
        name=filename,
    )


class _ImpersonatedUserNotFound(Exception):
    """Raised when a row's ``impersonate_as`` PK doesn't match an active user."""


class _ImpersonationClientCache:
    """
    Per-run pool of logged-in ``InternalHelixGraphQlClient`` instances, keyed
    by user PK. The bulk import has a small handful of distinct impersonated
    users (typically the IM team), so we open each login once and reuse the
    Django session across every row that targets that user.

    Must be used as a context manager so all cached sessions get logged out
    even if the run blows up partway through. Not thread-safe.
    """

    def __init__(self, default_user: User):
        self._default_user = default_user
        self._cache: typing.Dict[int, InternalHelixGraphQlClient] = {}
        self._stack = contextlib.ExitStack()

    def __enter__(self):
        self._stack.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return self._stack.__exit__(exc_type, exc_value, traceback)
        finally:
            self._cache.clear()

    def get_client(self, user_override: typing.Optional[User]) -> InternalHelixGraphQlClient:
        target = user_override or self._default_user
        if target.pk not in self._cache:
            self._cache[target.pk] = self._stack.enter_context(InternalHelixGraphQlClient(target))
        return self._cache[target.pk]


class HulkHelixModelImportBaseHandler:
    hulk_entity_relation_cls: type[HulkEntityRelationBase]
    hulk_entity_import_cls: type[HulkBaseModel]
    graphql_mutation_query: str

    def __init__(
        self,
        *,
        bulk_import: HulkBulkImport,
        client_cache: _ImpersonationClientCache,
    ):
        self.bulk_import = bulk_import
        self.client_cache = client_cache

        self.success_list = []
        self.error_list = []

    @abc.abstractmethod
    def graphql_response_parser_fn(self, response):
        raise NotImplementedError("graphql_response_parser_fn is missing")

    def graphql_response_parser_new_object_id(self, resp_create_obj):
        return resp_create_obj["result"]["id"]

    def graphql_response_parser_error(self, resp_create_obj):
        return resp_create_obj["errors"]

    def add_success(self, *, uuid: uuid.UUID, id: int, message: str):
        self.success_list.append(
            {
                "uuid": uuid,
                "id": id,
                "message": message,
            }
        )

    def add_error(self, *, uuid: uuid.UUID, error: dict):
        self.error_list.append(
            {
                "uuid": uuid,
                "error": error,
            }
        )

    def _handle_mutation(self, mutation: str, variables, *, user_override: typing.Optional[User] = None):
        client = self.client_cache.get_client(user_override)
        gql_data, gql_errors = client.run_mutation(mutation, variables)
        # This should't happen in theory - Should be validated using unit test cases
        if gql_errors:
            logger.error(
                "Error found on hulk bulk operation",
                extra={
                    "context": {
                        "bulk_operation_id": self.bulk_import.pk,
                        "variables": variables,
                        "data": gql_data,
                        "errors": gql_errors,
                    },
                },
            )

        return gql_data, gql_errors

    def _build_mutation_input(self, import_data) -> dict:
        """
        Hook: returns the dict passed as the ``input`` variable to the GraphQL
        mutation. Subclasses can override to inject extra fields (e.g. the
        attachment handler downloads a file and adds it under ``attachment``).
        Raise :class:`_InputBuildError` to record a post-error and skip the
        mutation.
        """
        return import_data.generate_for_graphql_mutation()

    def _create_entity(self, import_data, *, user_override: typing.Optional[User] = None) -> int:
        """
        Hook: create the helix entity for ``import_data`` and return its PK.

        Default implementation runs ``self.graphql_mutation_query`` once via
        ``_handle_mutation``. Subclasses can override to swap in a multi-step
        flow (e.g. the attachment handler's S3-copy fast path uses
        CreateBigAttachment → s3.copy_object → MarkBigAttachmentFileAsUploaded).

        Raise :class:`_CreateEntityError` to record a structured post-error.
        Raise :class:`_InputBuildError` from ``_build_mutation_input`` to
        record a string post-error.
        """
        obj_data = self._build_mutation_input(import_data)
        resp, errors = self._handle_mutation(
            self.graphql_mutation_query,
            {"input": obj_data},
            user_override=user_override,
        )
        if errors:
            raise _CreateEntityError(errors)
        resp_create_obj = self.graphql_response_parser_fn(resp) if resp else None
        # If the mutation responded without the expected payload (resp is empty,
        # parser_fn returned None/{}), fail the row with a structured post-error
        # instead of letting parser_error/_new_object_id raise KeyError/IndexError
        # and escape _CreateEntityError handling.
        if not resp_create_obj:
            raise _CreateEntityError(f"unexpected mutation response: {resp!r}")
        resp_errors = [_error for _error in resp_create_obj.get("errors") or [] if _error is not None]
        if resp_errors:
            raise _CreateEntityError(self.graphql_response_parser_error(resp_create_obj))
        return self.graphql_response_parser_new_object_id(resp_create_obj)

    def _resolve_impersonation(self, impersonate_as: typing.Optional[int]) -> typing.Optional[User]:
        if impersonate_as is None:
            return None
        user = User.objects.filter(pk=impersonate_as, is_active=True).first()
        if user is None:
            raise _ImpersonatedUserNotFound(f"impersonate_as user {impersonate_as} not found or inactive")
        return user

    def handle_row(self, row):
        row_uuid = row["uuid"]
        if row_uuid is None:
            return

        if hulk_obj := self.hulk_entity_relation_cls.objects.filter(uuid=row_uuid).first():
            logger.info("Already exists: %s", hulk_obj)
            self.add_success(uuid=row_uuid, id=hulk_obj.entity_id, message="Already exists")
            return

        try:
            hulk_obj_import_data = self.hulk_entity_import_cls.model_validate(row)
        except pydantic.ValidationError as pydantic_error:
            logger.warning(
                "Error while generating data for %s: %s",
                self.hulk_entity_relation_cls.get_entity_cls().__name__,
                hulk_obj or f"New(uuid={row_uuid})",
            )
            self.add_error(
                uuid=row_uuid,
                error={
                    PRE_ERROR_KEY: pydantic_error.errors(
                        include_context=False,
                        include_url=False,
                    )
                },
            )
            return
        except DatabaseError as db_error:
            # Validators on the import models hit the DB (e.g. get_name_attributed_model
            # lookups for sub-types). A transient OperationalError / DatabaseError there
            # would otherwise escape and abort the whole run — record it as a row-level
            # pre-error and let the rest of the rows proceed.
            logger.exception(
                "Database error while validating %s row uuid=%s",
                self.hulk_entity_relation_cls.get_entity_cls().__name__,
                row_uuid,
            )
            self.add_error(
                uuid=row_uuid,
                error={PRE_ERROR_KEY: f"database error during validation: {db_error}"},
            )
            return

        try:
            user_override = self._resolve_impersonation(hulk_obj_import_data.impersonate_as)
        except _ImpersonatedUserNotFound as e:
            self.add_error(uuid=row_uuid, error={PRE_ERROR_KEY: str(e)})
            return

        try:
            with transaction.atomic():
                new_obj_id = self._create_entity(hulk_obj_import_data, user_override=user_override)
                self.hulk_entity_relation_cls.objects.create(
                    bulk_import=self.bulk_import,
                    uuid=row_uuid,
                    entity_id=new_obj_id,
                )
        except _PreCheckError as e:
            self.add_error(uuid=row_uuid, error={PRE_ERROR_KEY: str(e)})
            return
        except _InputBuildError as e:
            self.add_error(uuid=row_uuid, error={POST_ERROR_KEY: str(e)})
            return
        except _CreateEntityError as e:
            self.add_error(uuid=row_uuid, error={POST_ERROR_KEY: e.payload})
            return
        except IntegrityError as e:
            self.add_error(uuid=row_uuid, error={POST_ERROR_KEY: f"relation insert failed: {e}"})
            return

        self.add_success(uuid=row_uuid, id=new_obj_id, message="Created")
        return


class HulkHelixAttachmentImportHandler(HulkHelixModelImportBaseHandler):
    hulk_entity_relation_cls = HulkAttachment
    hulk_entity_import_cls = HulkAttachmentImport
    # XXX: This may create orphan attachments — if ``createAttachment`` or
    #  the BigAttachment + copy_object + Mark sequence succeeds in the upload
    #  step but the HulkAttachment relation row creation fails afterwards, or
    #  if a downstream entry that references this uuid never imports, the
    #  Attachment is left dangling without any incoming reference.
    # ``createAttachment`` accepts an ``Upload!`` scalar — graphene-file-upload's
    # Upload is a passthrough, so we can call it through the standard mutation
    # path by attaching a Django file object as the ``attachment`` variable.
    graphql_mutation_query = """
        mutation HulkAttachmentMutation($input: AttachmentCreateInputType!) {
          __typename
          createAttachment(data: $input) {
            ok
            errors
            result {
              id
            }
          }
        }
    """

    # Mutations used by the S3-copy fast path.
    _CREATE_BIG_ATTACHMENT_QUERY = """
        mutation HulkCreateBigAttachment($input: BigAttachmentCreateInputType!) {
          createBigAttachment(data: $input) {
            ok
            errors
            result { id }
            s3PresignedUploadUrl
          }
        }
    """

    _MARK_BIG_ATTACHMENT_UPLOADED_QUERY = """
        mutation HulkMarkBigAttachmentUploaded($id: ID!) {
          markBigAttachmentFileAsUploaded(attachmentId: $id) {
            ok
            errors
            result { id }
          }
        }
    """

    # mimetype is mandatory on ``createBigAttachment`` but is overwritten when
    # ``markBigAttachmentFileAsUploaded`` sniffs the actual bytes via
    # ``AttachmentBoto3ConnectorService.verify_uploaded()``, so a placeholder
    # is fine.
    _BIG_ATTACHMENT_PLACEHOLDER_MIMETYPE = "application/pdf"

    def graphql_response_parser_fn(self, response):
        return response.get("createAttachment")

    def _build_mutation_input(self, import_data):
        try:
            attachment_file = download_file(import_data.file_url)
        except Exception as e:
            raise _InputBuildError(f"download failed: {e}")
        return {
            **import_data.generate_for_graphql_mutation(),
            "attachment": attachment_file,
        }

    def _create_entity(self, import_data, *, user_override: typing.Optional[User] = None) -> int:
        # AWS S3 URLs are only accepted from allowlisted buckets — anything
        # else fails the row outright (no httpx fallback) so we don't silently
        # stream bytes through helix from an unvetted source. Same-storage
        # URLs (helix's own MinIO/S3 endpoint) are implicitly trusted.
        aws_source = parse_aws_s3_url(import_data.file_url)
        if aws_source is not None:
            src_bucket, src_key = aws_source
            trusted = settings.HULK_TRUSTED_SOURCE_BUCKETS or []
            if src_bucket not in trusted:
                raise _PreCheckError(f"source bucket {src_bucket!r} is not in HULK_TRUSTED_SOURCE_BUCKETS allowlist")
            return self._create_via_s3_copy(
                import_data,
                src_bucket=src_bucket,
                src_key=src_key,
                user_override=user_override,
            )
        same_source = parse_same_storage_url(import_data.file_url)
        if same_source is not None:
            return self._create_via_s3_copy(
                import_data,
                src_bucket=same_source[0],
                src_key=same_source[1],
                user_override=user_override,
            )
        return super()._create_entity(import_data, user_override=user_override)

    # ------------------------------------------------------------------
    # S3-copy fast path
    # ------------------------------------------------------------------
    def _create_via_s3_copy(
        self,
        import_data,
        *,
        src_bucket: str,
        src_key: str,
        user_override: typing.Optional[User] = None,
    ) -> int:
        file_name = Path(src_key).name or "attachment"

        # Step 1: createBigAttachment — returns Attachment row + presigned PUT URL
        # whose host/path we use as the destination bucket/key.
        big_resp, big_errors = self._handle_mutation(
            self._CREATE_BIG_ATTACHMENT_QUERY,
            {
                "input": {
                    "fileName": file_name,
                    "attachmentFor": import_data.attachment_for.value,
                    "mimetype": self._BIG_ATTACHMENT_PLACEHOLDER_MIMETYPE,
                }
            },
            user_override=user_override,
        )
        if big_errors:
            raise _CreateEntityError(big_errors)
        big_payload = big_resp and big_resp.get("createBigAttachment") or {}
        if big_payload.get("errors"):
            raise _CreateEntityError(big_payload["errors"])
        attachment_id = (big_payload.get("result") or {}).get("id")
        presigned_url = big_payload.get("s3PresignedUploadUrl")
        if not attachment_id or not presigned_url:
            raise _CreateEntityError(f"createBigAttachment did not return id+presigned url: {big_payload!r}")

        # Step 2: parse the presigned URL → destination bucket + key. Try AWS
        # first, then fall back to same-storage (MinIO in dev) since the
        # presigned URL points at helix's configured endpoint either way.
        dst = parse_aws_s3_url(presigned_url) or parse_same_storage_url(presigned_url)
        if dst is None:
            raise _CreateEntityError(f"could not parse destination bucket/key from presigned url: {presigned_url!r}")
        dst_bucket, dst_key = dst

        # Step 3: server-side s3.copy_object. We use the helix media bucket's
        # boto3 client (default_storage) — it has the credentials to read the
        # source (if the IAM role allows it or the source is public-read)
        # and write the destination.
        try:
            client = default_storage.bucket.meta.client
            client.copy_object(
                CopySource={"Bucket": src_bucket, "Key": src_key},
                Bucket=dst_bucket,
                Key=dst_key,
            )
        except Exception as e:
            raise _CreateEntityError(f"s3.copy_object failed: {e}")

        # Step 4: markBigAttachmentFileAsUploaded — verifies the object exists,
        # sniffs mimetype with magic, then flips is_file_uploaded=True.
        mark_resp, mark_errors = self._handle_mutation(
            self._MARK_BIG_ATTACHMENT_UPLOADED_QUERY,
            {"id": attachment_id},
            user_override=user_override,
        )
        if mark_errors:
            raise _CreateEntityError(mark_errors)
        mark_payload = mark_resp and mark_resp.get("markBigAttachmentFileAsUploaded") or {}
        if mark_payload.get("errors"):
            raise _CreateEntityError(mark_payload["errors"])
        return int(attachment_id)


class HulkHelixSourcePreviewImportHandler(HulkHelixModelImportBaseHandler):
    hulk_entity_relation_cls = HulkSourcePreview
    hulk_entity_import_cls = HulkSourcePreviewImport
    # XXX: This may create orphan source previews — same concern as the
    #  attachment handler: the SourcePreview row exists after createSourcePreview
    #  even if no downstream entry references its uuid.
    # TODO: createSourcePreview currently only carries ``url``; once the
    #  HulkSourcePreviewImport gains versionId / token / pdf / status / remark,
    #  thread them through here too.
    graphql_mutation_query = """
        mutation HulkSourcePreviewMutation($input: SourcePreviewInputType!) {
          __typename
          createSourcePreview(data: $input) {
            ok
            errors
            result {
              id
            }
          }
        }
    """

    def graphql_response_parser_fn(self, response):
        return response.get("createSourcePreview")


class HulkHelixEntryImportHandler(HulkHelixModelImportBaseHandler):
    hulk_entity_relation_cls = HulkEntry
    hulk_entity_import_cls = HulkEntryImport
    graphql_mutation_query = """
        mutation HulkEntryMutation($input: EntryCreateInputType!) {
          __typename
          createEntry(data: $input) {
            ok
            errors
            result {
              id
            }
          }
        }
    """

    def graphql_response_parser_fn(self, response):
        return response.get("createEntry")


class HulkHelixEventImportHandler(HulkHelixModelImportBaseHandler):
    hulk_entity_relation_cls = HulkEvent
    hulk_entity_import_cls = HulkEventImport
    graphql_mutation_query = """
        mutation HulkEventMutation($input: EventCreateInputType!) {
          __typename
          createEvent(data: $input) {
            ok
            errors
            result {
              id
            }
          }
        }
    """

    def graphql_response_parser_fn(self, response):
        return response.get("createEvent")


class HulkHelixFigureImportHandler(HulkHelixModelImportBaseHandler):
    hulk_entity_relation_cls = HulkFigure
    hulk_entity_import_cls = HulkFigureImport
    graphql_mutation_query = """
        mutation HulkFigureMutation($input: FigureUpdateInputType!) {
          __typename
          bulkUpdateFigures(items: [$input]) {
            errors
            result {
              id
            }
          }
        }
    """

    def graphql_response_parser_new_object_id(self, resp_create_obj):
        return resp_create_obj["result"][0]["id"]

    def graphql_response_parser_error(self, resp_create_obj):
        return resp_create_obj["errors"][0]

    def graphql_response_parser_fn(self, response):
        return response.get("bulkUpdateFigures")


class HulkBulkImportHandler:
    def __init__(self, bulk_import: HulkBulkImport):
        self.bulk_import = bulk_import
        self.client_cache = _ImpersonationClientCache(default_user=bulk_import.created_by)

        # TODO: Add type check for include new handlers
        self.attachment_handler = HulkHelixAttachmentImportHandler(bulk_import=bulk_import, client_cache=self.client_cache)
        self.source_preview_handler = HulkHelixSourcePreviewImportHandler(
            bulk_import=bulk_import, client_cache=self.client_cache
        )
        self.entry_handler = HulkHelixEntryImportHandler(bulk_import=bulk_import, client_cache=self.client_cache)
        self.event_handler = HulkHelixEventImportHandler(bulk_import=bulk_import, client_cache=self.client_cache)
        self.figure_handler = HulkHelixFigureImportHandler(bulk_import=bulk_import, client_cache=self.client_cache)

        self.handlers = [
            self.attachment_handler,
            self.source_preview_handler,
            self.entry_handler,
            self.event_handler,
            self.figure_handler,
        ]

    def process(
        self,
        *,
        attachment_dataset: typing.Optional[typing.Generator[dict]],
        source_preview_dataset: typing.Optional[typing.Generator[dict]],
        entry_dataset: typing.Optional[typing.Generator[dict]],
        event_dataset: typing.Optional[typing.Generator[dict]],
        figure_dataset: typing.Optional[typing.Generator[dict]],
    ):
        # TODO: Add type check for include new handlers
        for handler, dataset in [
            (self.attachment_handler, attachment_dataset),
            (self.source_preview_handler, source_preview_dataset),
            (self.entry_handler, entry_dataset),
            (self.event_handler, event_dataset),
            (self.figure_handler, figure_dataset),
        ]:
            if dataset is None:
                logger.info("Nothing to process for TODO")
                continue

            for row in dataset:
                if isinstance(row, JsonlParseError):
                    handler.add_error(
                        uuid=None,
                        error={PRE_ERROR_KEY: f"malformed jsonl at line {row.line_no}: {row.message}"},
                    )
                    continue
                handler.handle_row(row)

    # Maps each ``HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE`` member to the handler
    # attribute that processes its rows. Iteration order is dependency order
    # — later types reference earlier ones by UUID, so we must always walk
    # attachments → source_previews → entries → events → figures regardless
    # of the order the user uploaded the datasets in.
    _HANDLER_BY_IMPORT_TYPE = (
        ("ATTACHMENT", "attachment_handler"),
        ("SOURCE_PREVIEW", "source_preview_handler"),
        ("ENTRY", "entry_handler"),
        ("EVENT", "event_handler"),
        ("FIGURE", "figure_handler"),
    )

    def _datasets_by_type(self) -> dict:
        """Return ``{HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.name: HulkBulkImportDataset row}`` for this bulk import."""
        from apps.hulk.models import HulkBulkImportDataset

        return {
            HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE(ds.import_type).name: ds
            for ds in self.bulk_import.datasets.all()
        }

    def _persist_results(self, datasets_by_type: dict):
        """
        Write each handler's success_list / error_list back to its
        ``HulkBulkImportDataset`` row. Aggregate counts are computed on read
        via the GraphQL resolver, so we only update per-dataset counters here.
        """
        for type_name, handler_attr in self._HANDLER_BY_IMPORT_TYPE:
            ds = datasets_by_type.get(type_name)
            if ds is None:
                continue
            handler = getattr(self, handler_attr)
            ds.success_count = len(handler.success_list)
            ds.failure_count = len(handler.error_list)
            update_fields = ["success_count", "failure_count"]
            if handler.success_list:
                ds.success_file.save(
                    "success.jsonl",
                    ContentFile(dump_jsonl(handler.success_list)),
                    save=False,
                )
                update_fields.append("success_file")
            if handler.error_list:
                ds.failure_file.save(
                    "failure.jsonl",
                    ContentFile(dump_jsonl(handler.error_list)),
                    save=False,
                )
                update_fields.append("failure_file")
            ds.save(update_fields=update_fields)

    def handle(self) -> bool:
        # Compare-and-set PENDING -> IN_PROGRESS at the row level. Guards
        # against double-runs (retries, accidental re-dispatch, two workers
        # picking up the same row) by relying on the DB to serialize the
        # transition: only one caller observes ``updated == 1``. The global
        # "no overlapping bulk imports" rule is enforced by the serializer at
        # creation time; this CAS just makes sure a given row never starts
        # twice.
        now = timezone.now()
        updated = HulkBulkImport.objects.filter(
            pk=self.bulk_import.pk,
            status=HulkBulkImport.HULK_BULK_IMPORT_STATUS.PENDING,
        ).update(
            status=HulkBulkImport.HULK_BULK_IMPORT_STATUS.IN_PROGRESS,
            started_at=now,
        )
        if updated == 0:
            self.bulk_import.refresh_from_db()
            logger.warning(
                "Skipping hulk bulk import %s: status=%s (not PENDING)",
                self.bulk_import.pk,
                self.bulk_import.get_status_display(),
            )
            return False
        # Sync the in-memory instance so downstream code sees IN_PROGRESS.
        self.bulk_import.status = HulkBulkImport.HULK_BULK_IMPORT_STATUS.IN_PROGRESS
        self.bulk_import.started_at = now
        datasets_by_type = self._datasets_by_type()
        succeeded = False
        try:
            with self.client_cache:
                self.process(
                    attachment_dataset=iter_jsonl_field(
                        datasets_by_type["ATTACHMENT"].import_file if "ATTACHMENT" in datasets_by_type else None
                    ),
                    source_preview_dataset=iter_jsonl_field(
                        datasets_by_type["SOURCE_PREVIEW"].import_file if "SOURCE_PREVIEW" in datasets_by_type else None
                    ),
                    entry_dataset=iter_jsonl_field(
                        datasets_by_type["ENTRY"].import_file if "ENTRY" in datasets_by_type else None
                    ),
                    event_dataset=iter_jsonl_field(
                        datasets_by_type["EVENT"].import_file if "EVENT" in datasets_by_type else None
                    ),
                    figure_dataset=iter_jsonl_field(
                        datasets_by_type["FIGURE"].import_file if "FIGURE" in datasets_by_type else None
                    ),
                )
            succeeded = True
        except Exception:
            logger.exception("Failed to process hulk bulk import: %s", self.bulk_import.pk)
        finally:
            try:
                self._persist_results(datasets_by_type)
            except Exception:
                logger.exception("Failed to persist results for hulk bulk import: %s", self.bulk_import.pk)
                succeeded = False
        if succeeded:
            self.bulk_import.update_status(HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)
            return True
        self.bulk_import.update_status(HulkBulkImport.HULK_BULK_IMPORT_STATUS.FAILED)
        return False
