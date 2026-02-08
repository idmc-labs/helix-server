from __future__ import annotations

import abc
import cgi
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

from apps.contrib.bulk_operations.tasks import InternalHelixGraphQlClient
from apps.contrib.models import Attachment, SourcePreview
from apps.contrib.serializers import AttachmentSerializer, SourcePreviewSerializer
from apps.entry.models import Figure
from apps.event.models import Event
from apps.hulk.models import (
    HulkAttachment,
    HulkBulkImport,
    HulkEntityRelationBase,
    HulkEntry,
    HulkEvent,
    HulkFigure,
    HulkSourcePreview,
)
from utils.error_types import mutation_is_not_valid

from .models import (
    HulkAttachmentImport,
    HulkBaseModel,
    HulkEntryImport,
    HulkEventImport,
    HulkFigureImport,
    HulkSourcePreviewImport,
)

logger = logging.getLogger(__name__)

# TODO: Is this okay?
PRE_ERROR_KEY = "pre-errors"
POST_ERROR_KEY = "post-errors"


def load_jsonl(path) -> typing.Generator[dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:  # skip empty lines
                yield json.loads(line)


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


# TODO: Handle for large files
# TODO: Use s3.copy_object to copy file from hulk s3 to helix s3
def download_file(url):
    response = httpx.get(url)

    # TODO: Check if this works for all cases
    filename = get_filename_from_response(response, fallback="attachment")

    return ContentFile(
        response.content,
        name=filename,
    )


class HulkHelixModelImportBaseHandler:
    hulk_entity_relation_cls: type[HulkEntityRelationBase]
    hulk_entity_import_cls: type[HulkBaseModel]
    graphql_mutation_query: str

    def __init__(
        self,
        *,
        bulk_import: HulkBulkImport,
    ):
        self.bulk_import = bulk_import

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

    def _handle_mutation(self, mutation: str, variables):
        # TODO: Move the created_by client to __init__ and use that instead of creating for each
        with InternalHelixGraphQlClient(self.bulk_import.created_by) as client:
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

        obj_data = hulk_obj_import_data.generate_for_graphql_mutation()

        resp, errors = self._handle_mutation(
            self.graphql_mutation_query,
            {"input": obj_data},
        )

        # NOTE: Handling success
        resp_create_obj = resp and self.graphql_response_parser_fn(resp) or {}
        resp_create_obj_ok = (
            resp_create_obj and len([_error for _error in resp_create_obj.get("errors") or [] if _error is not None]) == 0
        )

        if resp_create_obj_ok:
            # TODO: Optimize?
            new_obj_id = self.graphql_response_parser_new_object_id(resp_create_obj)
            self.hulk_entity_relation_cls.objects.create(
                bulk_import=self.bulk_import,
                uuid=row_uuid,
                entity_id=new_obj_id,
            )
            self.add_success(
                uuid=row_uuid,
                id=new_obj_id,
                message="Created",
            )
            return

        # NOTE: Handling error
        error = "Unknown error"
        if errors:
            # GraphQl validation error
            error = errors
        elif resp_create_obj_ok is False:
            # Serializer validation error
            error = self.graphql_response_parser_error(resp_create_obj)
        self.add_error(uuid=row_uuid, error={POST_ERROR_KEY: error})


class HulkHelixAttachmentImportHandler(HulkHelixModelImportBaseHandler):
    hulk_entity_relation_cls = HulkAttachment
    hulk_entity_import_cls = HulkAttachmentImport
    # TODO
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

    def graphql_response_parser_fn(self, response):
        return response.get("createAttachment")


class HulkHelixSourcePreviewImportHandler(HulkHelixModelImportBaseHandler):
    hulk_entity_relation_cls = HulkSourcePreview
    hulk_entity_import_cls = HulkSourcePreviewImport
    # TODO
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

        # TODO: Add type check for include new handlers
        self.attachment_handler = HulkHelixAttachmentImportHandler(bulk_import=bulk_import)
        self.source_preview_handler = HulkHelixSourcePreviewImportHandler(bulk_import=bulk_import)
        self.entry_handler = HulkHelixEntryImportHandler(bulk_import=bulk_import)
        self.event_handler = HulkHelixEventImportHandler(bulk_import=bulk_import)
        self.figure_handler = HulkHelixFigureImportHandler(bulk_import=bulk_import)

        self.handlers = [
            self.attachment_handler,
            self.source_preview_handler,
            self.entry_handler,
            self.event_handler,
            self.figure_handler,
        ]

    @staticmethod
    def _generate_snapshot(existing_events: typing.List[Event], existing_figures: typing.List[Figure]):
        # # Circular dependency
        # from apps.contrib.tasks import get_excel_sheet_content

        # qs = Figure.objects.filter(id__in=[item.pk for item in existing_figures])

        # sheet_data = Figure.get_figure_excel_sheets_data(qs)
        # workbook = get_excel_sheet_content(**sheet_data)
        # save_workbook_file(operation, workbook)
        ...

    def _create_attachment(
        self,
        url: str,
    ) -> typing.Union[
        tuple[None, list[dict]],
        tuple[Attachment, None],
    ]:
        # TODO: This may create orphan attachments
        with InternalHelixGraphQlClient(self.bulk_import.created_by) as client:
            # TODO: Use s3.copy_object to copy file from hulk s3 to helix s3
            #  https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/copy_object.html
            attachment_file = download_file(url)
            serializer = AttachmentSerializer(
                context={"request": client.api_request},
                data={"attachment": attachment_file},
            )
            if errors := mutation_is_not_valid(serializer):
                return None, errors
            return typing.cast("Attachment", serializer.save()), None

    def _handle_source_preview(
        self,
        url: str,
    ) -> typing.Union[
        tuple[None, list[dict]],
        tuple[SourcePreview, None],
    ]:
        # TODO: This may create orphan source previews
        with InternalHelixGraphQlClient(self.bulk_import.created_by) as client:
            serializer = SourcePreviewSerializer(
                context={"request": client.api_request},
                data={"url": url},
            )
            if errors := mutation_is_not_valid(serializer):
                return None, errors
            return typing.cast("SourcePreview", serializer.save()), None

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
                handler.handle_row(row)

    def handle(self) -> bool:
        # FIXME: Add a lock, so that only one bulk import is running at a time using redis lock

        base_path = settings.BASE_DIR / Path("temp/somalia-2026")
        self.process(
            attachment_dataset=load_jsonl(base_path / "attachments.jsonl"),
            source_preview_dataset=load_jsonl(base_path / "source_previews.jsonl"),
            entry_dataset=load_jsonl(base_path / "entries.jsonl"),
            event_dataset=load_jsonl(base_path / "events.jsonl"),
            figure_dataset=load_jsonl(base_path / "figures.jsonl"),
        )

        # self.bulk_import.update_status(HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED, commit=False)
        # self.bulk_import.save()
        print("Output", "*" * 22)

        print("Success: -------------------")
        for handler in self.handlers:
            print(f"--- {handler.__class__} ---")
            for success_data in handler.success_list:
                print("\033[32;44m--> \033[0m", success_data)

        print("Errors: -------------------")
        for handler in self.handlers:
            print(f"--- {handler.__class__} ---")
            for error_data in handler.error_list:
                print("\033[31;43m--> \033[0m", error_data)

        for handler in self.handlers:
            print(f"--- {handler.__class__} ---")
            print("Error: ", len(handler.error_list))
            print("Success: ", len(handler.success_list))
        return True

        # try:
        #     now = timezone.now()
        #     if now - self.bulk_import.created_at > datetime.timedelta(minutes=HulkBulkImport.WAIT_TIME_THRESHOLD_IN_MINUTES):
        #         logger.warning("Skipping bulk bulk_import: %s", self.bulk_import.pk)
        #         self.bulk_import.update_status(HulkBulkImport.HULK_BULK_IMPORT_STATUS.SKIPPED)
        #         return False
        #     logger.info("Processing Hulk bulk import: %s", self.bulk_import.pk)
        #     self.bulk_import.update_status(HulkBulkImport.HULK_BULK_IMPORT_STATUS.IN_PROGRESS)
        #     workbook = load_workbook(self.bulk_import.payload, data_only=True, read_only=True)
        #     self.process(workbook)
        # except Exception:
        #     logger.error("Failed to process hulk bulk import: %s", self.bulk_import.pk, exc_info=True)
        #     self.bulk_import.update_status(HulkBulkImport.HULK_BULK_IMPORT_STATUS.FAILED)
        #     return False
        # return True
