"""
Unit + component tests for the hulk bulk-import handler.

The handler talks to helix via ``InternalHelixGraphQlClient`` (which runs
GraphQL mutations against the in-process schema). To keep these tests fast and
isolated from helix-side validation, we patch the client and the attachment
download helper; the schema mutations themselves are exercised end-to-end in
``test_apis.py``.

Scope here:
    - JSONL helpers (``dump_jsonl`` round-trips through ``iter_jsonl_field``)
    - ``HulkBulkImportHandler.handle()``:
        * reads input from model file fields, writes output to model file fields
        * records pydantic ``pre-errors``
        * records GraphQL ``post-errors``
        * updates status / success_count / failure_count
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.test import override_settings

from apps.hulk.bulk.handler import (
    HulkBulkImportHandler,
    JsonlParseError,
    _normalize_graphql_errors,
    dump_jsonl,
    iter_jsonl_field,
)
from apps.hulk.bulk.utils import parse_aws_s3_url, parse_same_storage_url
from apps.hulk.models import HulkBulkImport, HulkBulkImportDataset
from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    DisasterSubTypeFactory,
    OrganizationFactory,
    OtherSubtypeFactory,
    ViolenceSubTypeFactory,
)
from utils.tests import HelixGraphQLTestCase, create_user_with_role

from .fixtures import (
    EVENT_UUIDS,
    EXPECTED_OUTCOMES,
    RESOURCES,
    FixtureContext,
    build_jsonl_bundle,
    read_expected_failure,
    read_expected_input_rows,
    read_expected_success,
)

# Subset of expected outcomes that the mocked GraphQL client preserves:
# pydantic-level errors fire regardless of what the client returns. The other
# expected failures (helix serializer post-errors) only land under the real
# schema, so under the mocked-success client they appear in success_* instead.
PYDANTIC_ONLY_FAILURE_UUIDS = {
    resource: {
        uuid
        for uuid, outcome in EXPECTED_OUTCOMES[resource].items()
        if outcome["outcome"] == "failure" and outcome["error_key"] == "pre-errors"
    }
    for resource in RESOURCES
}


def _make_ctx() -> FixtureContext:
    return FixtureContext(
        country_id=CountryFactory.create(iso2="NP", iso3="NPL", idmc_short_name="Nepal").id,
        publisher_id=OrganizationFactory.create().id,
        source_id=OrganizationFactory.create().id,
        violence_sub_type_id=ViolenceSubTypeFactory.create().id,
        disaster_sub_type_id=DisasterSubTypeFactory.create().id,
        other_sub_type_id=OtherSubtypeFactory.create().id,
    )


# Short resource name → HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE enum member.
_TYPE_FOR_RESOURCE = {
    "attachments": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.ATTACHMENT,
    "source_previews": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.SOURCE_PREVIEW,
    "entries": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.ENTRY,
    "events": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.EVENT,
    "figures": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.FIGURE,
}


def _create_dataset(bulk: HulkBulkImport, resource: str, payload: bytes) -> HulkBulkImportDataset:
    """Helper: create + populate a ``HulkBulkImportDataset`` row for one resource."""
    ds = HulkBulkImportDataset.objects.create(
        bulk_import=bulk,
        import_type=_TYPE_FOR_RESOURCE[resource].value,
    )
    ds.import_file.save(f"{resource}.jsonl", ContentFile(payload), save=True)
    return ds


def _dataset_for(bulk: HulkBulkImport, resource: str) -> HulkBulkImportDataset:
    return bulk.datasets.get(import_type=_TYPE_FOR_RESOURCE[resource].value)


def _attach_inputs(instance: HulkBulkImport, bundle: dict) -> None:
    """Attach all five resources from a fixture bundle as dataset rows."""
    for resource in ("attachments", "source_previews", "entries", "events", "figures"):
        _create_dataset(instance, resource, bundle[resource])


def _success_file(bulk: HulkBulkImport, resource: str):
    return _dataset_for(bulk, resource).success_file


def _failure_file(bulk: HulkBulkImport, resource: str):
    return _dataset_for(bulk, resource).failure_file


def _aggregate_counts(bulk: HulkBulkImport) -> tuple[int, int]:
    """Compute (success_count, failure_count) by summing dataset rows."""
    s = sum(ds.success_count or 0 for ds in bulk.datasets.all())
    f = sum(ds.failure_count or 0 for ds in bulk.datasets.all())
    return s, f


def _jsonl_rows(field_file) -> list[dict]:
    gen = iter_jsonl_field(field_file)
    if gen is None:
        return []
    return list(gen)


class TestJsonlHelpers(HelixGraphQLTestCase):
    def test_dump_and_iter_round_trip(self):
        user = create_user_with_role(USER_ROLE.ADMIN.name)
        bulk = HulkBulkImport.objects.create(created_by=user)
        ds = HulkBulkImportDataset.objects.create(
            bulk_import=bulk,
            import_type=HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.ENTRY.value,
        )

        rows = [
            {"uuid": "u-1", "id": 11, "message": "Created"},
            {"uuid": "u-2", "id": 12, "message": "Already exists"},
        ]
        ds.success_file.save("success.jsonl", ContentFile(dump_jsonl(rows)), save=True)

        ds.refresh_from_db()
        round_trip = _jsonl_rows(ds.success_file)
        self.assertEqual(round_trip, rows)

    def test_iter_jsonl_field_returns_none_for_empty_field(self):
        user = create_user_with_role(USER_ROLE.ADMIN.name)
        bulk = HulkBulkImport.objects.create(created_by=user)
        ds = HulkBulkImportDataset.objects.create(
            bulk_import=bulk,
            import_type=HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.ENTRY.value,
        )
        self.assertIsNone(iter_jsonl_field(ds.import_file))

    def test_iter_jsonl_field_yields_sentinel_for_malformed_line(self):
        """
        Malformed JSON lines yield a ``JsonlParseError`` sentinel instead of
        raising — so the import loop can record a per-row pre-error and keep
        going rather than aborting the entire run.
        """
        user = create_user_with_role(USER_ROLE.ADMIN.name)
        bulk = HulkBulkImport.objects.create(created_by=user)
        ds = HulkBulkImportDataset.objects.create(
            bulk_import=bulk,
            import_type=HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.ENTRY.value,
        )
        # line 1: valid; line 2: malformed JSON; line 3: valid.
        payload = b'{"uuid": "u-1"}\n{not json\n{"uuid": "u-3"}\n'
        ds.import_file.save("entries.jsonl", ContentFile(payload), save=True)
        ds.refresh_from_db()

        results = _jsonl_rows(ds.import_file)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0], {"uuid": "u-1"})
        self.assertIsInstance(results[1], JsonlParseError)
        self.assertEqual(results[1].line_no, 2)
        self.assertIn("invalid json", results[1].message)
        self.assertEqual(results[2], {"uuid": "u-3"})

    def test_parse_aws_s3_url(self):
        """Only AWS S3 URLs should resolve to (bucket, key); MinIO/CDN return None."""
        cases = [
            # Virtual-hosted style
            ("https://my-bucket.s3.amazonaws.com/k.pdf", ("my-bucket", "k.pdf")),
            ("https://my-bucket.s3.us-east-1.amazonaws.com/folder/k.pdf", ("my-bucket", "folder/k.pdf")),
            # Legacy hyphenated region
            ("https://my-bucket.s3-us-west-2.amazonaws.com/k.pdf", ("my-bucket", "k.pdf")),
            # Path-style
            ("https://s3.amazonaws.com/my-bucket/k.pdf", ("my-bucket", "k.pdf")),
            ("https://s3.eu-central-1.amazonaws.com/my-bucket/k.pdf", ("my-bucket", "k.pdf")),
            # s3:// scheme
            ("s3://my-bucket/folder/x.pdf", ("my-bucket", "folder/x.pdf")),
            # Presigned URL (query string is not part of the key)
            (
                "https://my-bucket.s3.amazonaws.com/k.pdf?X-Amz-Signature=abc&X-Amz-Date=20260512",
                ("my-bucket", "k.pdf"),
            ),
            # Non-S3 hosts
            ("http://localhost:9002/helix-data/x.pdf", None),  # MinIO
            ("https://cdn.example.com/x.pdf", None),
            ("https://my-bucket.example.amazonaws.com/k.pdf", None),  # not s3.*
            # Edge cases
            ("", None),
            ("not-a-url", None),
            ("https://my-bucket.s3.amazonaws.com/", None),  # bucket but no key
        ]
        for url, expected in cases:
            with self.subTest(url=url):
                source = parse_aws_s3_url(url)
                if expected is None:
                    self.assertIsNone(source)
                    continue
                self.assertEqual((source.bucket, source.key), expected)

    def test_parse_aws_s3_url_key_candidates_for_literal_percent(self):
        """
        A percent sequence in the URL path has two readings, so both are
        offered as candidates (best guess first) instead of committing to one:

        * an http(s) URL is meant to be percent-encoded → decode once, and keep
          the undecoded path as a fallback for exporters that pasted the raw key,
        * an ``s3://`` URI carries the literal key → the reverse order.
        """
        http_source = parse_aws_s3_url("https://my-bucket.s3.amazonaws.com/in/report%20final.pdf")
        self.assertEqual(http_source.key, "in/report final.pdf")
        self.assertEqual(http_source.key_candidates, ("in/report final.pdf", "in/report%20final.pdf"))

        # Canonically encoded URL for the key that literally contains "%20".
        encoded_source = parse_aws_s3_url("https://my-bucket.s3.amazonaws.com/in/report%2520final.pdf")
        self.assertEqual(encoded_source.key, "in/report%20final.pdf")
        self.assertEqual(encoded_source.key_candidates, ("in/report%20final.pdf", "in/report%2520final.pdf"))

        # s3:// → literal key wins.
        s3_source = parse_aws_s3_url("s3://my-bucket/in/100%25done.pdf")
        self.assertEqual(s3_source.key, "in/100%25done.pdf")
        self.assertEqual(s3_source.key_candidates, ("in/100%25done.pdf", "in/100%done.pdf"))

        # Nothing to disambiguate → a single candidate.
        plain = parse_aws_s3_url("https://my-bucket.s3.amazonaws.com/in/plain.pdf")
        self.assertEqual(plain.key_candidates, ("in/plain.pdf",))

    def test_parse_aws_s3_url_detects_presigned_urls(self):
        """``is_presigned`` flags URLs whose query carries an AWS signature."""
        cases = [
            ("https://b.s3.amazonaws.com/k.pdf", False),
            ("https://b.s3.amazonaws.com/k.pdf?versionId=abc", False),
            # SigV4
            ("https://b.s3.amazonaws.com/k.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=ab", True),
            ("https://b.s3.amazonaws.com/k.pdf?x-amz-signature=ab", True),  # case-insensitive
            # SigV2 (legacy)
            ("https://b.s3.amazonaws.com/k.pdf?AWSAccessKeyId=AK&Signature=ab&Expires=1", True),
        ]
        for url, expected in cases:
            with self.subTest(url=url):
                self.assertEqual(parse_aws_s3_url(url).is_presigned, expected)

    @override_settings(AWS_S3_ENDPOINT_URL="http://minio:9000")
    def test_parse_same_storage_url_with_endpoint_configured(self):
        # Parsers return the literal path-after-bucket from the URL. We do
        # *not* strip any storage-location prefix (e.g. ``media/``): the
        # actual S3 object key includes that prefix — Django's
        # ``FieldFile.name`` is what's relative to ``storage.location``, but
        # boto3 operates on the absolute key.
        cases = [
            ("http://minio:9000/helix-data/media/x.pdf", ("helix-data", "media/x.pdf")),
            ("http://minio:9000/bucket/key", ("bucket", "key")),
            # Different host (port-forward form) → not same-storage.
            ("http://localhost:9002/helix-data/x.pdf", None),
            # AWS S3 URLs are handled by parse_aws_s3_url, not this one.
            ("https://my.s3.amazonaws.com/key", None),
            # Bucket-only / missing key.
            ("http://minio:9000/onlybucket", None),
            ("", None),
        ]
        for url, expected in cases:
            with self.subTest(url=url):
                source = parse_same_storage_url(url)
                if expected is None:
                    self.assertIsNone(source)
                    continue
                self.assertEqual((source.bucket, source.key), expected)

    @override_settings(AWS_S3_ENDPOINT_URL="http://minio:9000")
    def test_parse_same_storage_url_key_candidates_and_presigned(self):
        source = parse_same_storage_url("http://minio:9000/helix-data/media/a%20b.pdf?X-Amz-Signature=x")
        self.assertEqual(source.bucket, "helix-data")
        self.assertEqual(source.key_candidates, ("media/a b.pdf", "media/a%20b.pdf"))
        self.assertTrue(source.is_presigned)

    @override_settings(AWS_S3_ENDPOINT_URL=None)
    def test_parse_same_storage_url_without_endpoint(self):
        """No AWS_S3_ENDPOINT_URL configured → every URL returns None."""
        self.assertIsNone(parse_same_storage_url("http://minio:9000/bucket/key"))


class _CountingResponder:
    """
    Stand-in for the GraphQL client. Instead of calling helix's real schema
    (which would re-validate the payload and is exercised in test_apis.py),
    we create a real Django row of the appropriate entity type so the HulkEntry/
    HulkEvent/HulkFigure FK insert succeeds, then return that row's id.
    """

    def __init__(self):
        from utils.factories import (
            EntryFactory,
            EventFactory,
            FigureFactory,
        )

        self.entry_factory = EntryFactory
        self.event_factory = EventFactory
        self.figure_factory = FigureFactory
        # Cache one Event so FigureFactory rows can satisfy the non-null event FK.
        self._event_for_figures = None

    def __call__(self, query: str, variables: dict):
        if "createBigAttachment" in query:
            # Mirror BigAttachmentSerializer.create + its presigned-url field:
            # the handler parses the returned url for the destination bucket/key,
            # so it has to be a real one for the real storage backend.
            from apps.contrib.models import Attachment, global_upload_to
            from apps.contrib.utils import AttachmentBoto3ConnectorService

            obj = Attachment(
                attachment_for=variables["input"]["attachmentFor"],
                mimetype=variables["input"]["mimetype"],
                is_file_uploaded=False,
            )
            obj.attachment.name = global_upload_to(obj, variables["input"]["fileName"])
            obj.save()
            return (
                {
                    "createBigAttachment": {
                        "ok": True,
                        "errors": None,
                        "result": {"id": obj.pk},
                        "s3PresignedUploadUrl": AttachmentBoto3ConnectorService(instance=obj).get_attachment_presigned_url(),
                    }
                },
                None,
            )
        if "markBigAttachmentFileAsUploaded" in query:
            from apps.contrib.models import Attachment

            Attachment.objects.filter(pk=variables["id"]).update(is_file_uploaded=True)
            return (
                {"markBigAttachmentFileAsUploaded": {"ok": True, "errors": None, "result": {"id": variables["id"]}}},
                None,
            )
        if "createSourcePreview" in query:
            from apps.contrib.models import SourcePreview

            obj = SourcePreview.objects.create(url=variables["input"].get("url", "https://example.com"))
            return ({"createSourcePreview": {"ok": True, "errors": None, "result": {"id": obj.pk}}}, None)
        if "createEntry" in query:
            obj = self.entry_factory.create()
            return ({"createEntry": {"ok": True, "errors": None, "result": {"id": obj.pk}}}, None)
        if "createEvent" in query:
            from apps.crisis.models import Crisis

            # Mirror the requested event_type so downstream figure validation
            # (which keys on Event.event_type) sees the right cause.
            event_type_name = variables["input"].get("eventType") or Crisis.CRISIS_TYPE.DISASTER.name
            obj = self.event_factory.create(event_type=Crisis.CRISIS_TYPE[event_type_name].value)
            return ({"createEvent": {"ok": True, "errors": None, "result": {"id": obj.pk}}}, None)
        if "bulkUpdateFigures" in query:
            if self._event_for_figures is None:
                self._event_for_figures = self.event_factory.create()
            obj = self.figure_factory.create(
                entry=self.entry_factory.create(),
                event=self._event_for_figures,
            )
            return (
                {"bulkUpdateFigures": {"errors": [None], "result": [{"id": obj.pk}]}},
                None,
            )
        return ({}, None)


# A minimal valid PDF body the attachment downloader can hand off to AttachmentSerializer.
_DUMMY_PDF_BYTES = (
    b"%PDF-1.1\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 99 99]/Parent 2 0 R/Resources<<>>>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n164\n%%EOF\n"
)


def _patch_download_file():
    """
    Patch ``download_file`` so the attachment handler doesn't hit the network.
    ``side_effect`` yields a fresh ContentFile per call — the handler reads the
    file to upload it, so reusing one ContentFile across rows would let only the
    first attachment succeed.
    """
    from django.core.files.base import ContentFile

    return patch(
        "apps.hulk.bulk.handler.download_file",
        side_effect=lambda url: ContentFile(_DUMMY_PDF_BYTES, name="dummy.pdf"),
    )


class TestHulkBulkImportHandler(HelixGraphQLTestCase):
    """
    These tests patch ``InternalHelixGraphQlClient`` so the handler returns
    canned responses. The handler's own pre-/post-error wiring, file IO and
    status transitions are what is being asserted.
    """

    def setUp(self):
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.ctx = _make_ctx()

    def _make_bulk_import_with_inputs(self) -> HulkBulkImport:
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        _attach_inputs(bulk, build_jsonl_bundle(self.ctx))
        return bulk

    def test_handle_success_path(self):
        """
        Run the handler with a mocked GraphQL client that always returns
        ``ok=True``. Under this mock, only the pydantic-level pre-errors
        (entries.bad_no_ref, figures.missing_event) end up in failure files;
        everything else lands in the corresponding success file.

        Asserts per-resource:
          * exact set of UUIDs in success_<resource>
          * exact set of UUIDs in failure_<resource>
          * shape of each success row: {uuid, id (int), message: "Created"}
          * shape of each failure row: {uuid, error: {<key>: ...}}
          * total counts equal the fixture row count
        """
        bulk = self._make_bulk_import_with_inputs()

        attachment_patch = _patch_download_file()
        with attachment_patch, patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _CountingResponder()
            MockClient.return_value.__enter__.return_value = mock_client

            handler = HulkBulkImportHandler(bulk)
            handler.handle()

        bulk.refresh_from_db()
        self.assertEqual(bulk.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)
        self.assertIsNotNone(bulk.started_at)
        self.assertIsNotNone(bulk.completed_at)

        total_success = 0
        total_failure = 0
        for resource in RESOURCES:
            input_rows = read_expected_input_rows(resource)
            input_uuids = {r["uuid"] for r in input_rows}
            expected_failure_uuids = PYDANTIC_ONLY_FAILURE_UUIDS[resource]
            expected_success_uuids = input_uuids - expected_failure_uuids

            success_rows = _jsonl_rows(_success_file(bulk, resource))
            failure_rows = _jsonl_rows(_failure_file(bulk, resource))

            with self.subTest(resource=resource, side="success"):
                self.assertEqual({r["uuid"] for r in success_rows}, expected_success_uuids)
                for row in success_rows:
                    self.assertEqual(set(row.keys()), {"uuid", "id", "message"})
                    self.assertIsInstance(row["id"], int)
                    self.assertEqual(row["message"], "Created")

            with self.subTest(resource=resource, side="failure"):
                self.assertEqual({r["uuid"] for r in failure_rows}, expected_failure_uuids)
                for row in failure_rows:
                    self.assertEqual(set(row.keys()), {"uuid", "error"})
                    # Under the mocked-success client every failure here is a
                    # pydantic pre-error — the post-error path is exercised in
                    # test_handle_post_error_recorded.
                    self.assertIn("pre-errors", row["error"])
                    # Each failure row must carry the substring the fixture
                    # declares — guards against silent regressions where a
                    # validator changes wording or fires for the wrong reason.
                    expected_match = EXPECTED_OUTCOMES[resource][row["uuid"]]["error_match"]
                    self.assertIn(
                        expected_match,
                        json.dumps(row["error"], default=str),
                        f"{resource}/{row['uuid']}: expected error containing {expected_match!r}",
                    )

            total_success += len(success_rows)
            total_failure += len(failure_rows)

        # Aggregate counters match.
        self.assertEqual(_aggregate_counts(bulk)[0], total_success)
        self.assertEqual(_aggregate_counts(bulk)[1], total_failure)
        # Sanity: every fixture row landed somewhere.
        total_fixture_rows = sum(len(read_expected_input_rows(r)) for r in RESOURCES)
        self.assertEqual(total_success + total_failure, total_fixture_rows)

    def test_handle_post_error_recorded(self):
        """When the GraphQL client returns errors, the row lands in failure_* with post-errors.

        Only events that pass pyhelix pre-validation actually invoke
        ``createEvent`` — the ``blank_narrative`` row is caught client-side
        and lands as a pre-error. The mock here covers the post-error path
        for every other event using a real helix-only rule (``event_codes``
        max length of 50, enforced by ``EventSerializer._validate_event_codes``
        and not pre-checked by pyhelix).
        """
        bulk = self._make_bulk_import_with_inputs()

        expected_match = "More than 50 event codes are not allowed"

        def _gql_response(query, variables):
            if "createEvent" in query:
                return (
                    {
                        "createEvent": {
                            "ok": False,
                            "errors": [{"field": "eventCodes", "messages": expected_match}],
                            "result": None,
                        }
                    },
                    None,
                )
            return _CountingResponder()(query, variables)

        attachment_patch = _patch_download_file()
        with attachment_patch, patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _gql_response
            MockClient.return_value.__enter__.return_value = mock_client

            HulkBulkImportHandler(bulk).handle()

        bulk.refresh_from_db()
        failure_events = _jsonl_rows(_failure_file(bulk, "events"))
        # Every fixture event lands in failure: the pre-rejected ones with
        # pre-errors, every attempted one with post-errors.
        self.assertEqual({r["uuid"] for r in failure_events}, set(EVENT_UUIDS.values()))

        attempted_uuids = set(EVENT_UUIDS.values()) - PYDANTIC_ONLY_FAILURE_UUIDS["events"]
        self.assertGreater(len(attempted_uuids), 0)
        rows_by_uuid = {r["uuid"]: r for r in failure_events}
        for u in attempted_uuids:
            row = rows_by_uuid[u]
            self.assertIn("post-errors", row["error"])
            self.assertEqual(row["error"]["post-errors"][0]["field"], "eventCodes")
            self.assertIn(expected_match, row["error"]["post-errors"][0]["messages"])

    def test_handle_figure_post_error_for_bad_country_iso2_mismatch(self):
        """
        Mock the figure mutation to return helix's real iso2-mismatch error and
        confirm the ``bad_country`` figure (and only that one) lands in
        failure_figures with the substring declared in EXPECTED_OUTCOMES.
        """
        from apps.hulk.bulk.handler import HulkHelixFigureImportHandler  # noqa: F401  (ensures import wires up)
        from apps.hulk.tests.fixtures import FIGURE_UUIDS as F

        bulk = self._make_bulk_import_with_inputs()

        expected_match = EXPECTED_OUTCOMES["figures"][F["bad_country"]]["error_match"]

        responder = _CountingResponder()

        def _gql_response(query, variables):
            if "bulkUpdateFigures" in query:
                figure_uuid = (variables.get("input") or {}).get("uuid")
                if figure_uuid == F["bad_country"]:
                    return (
                        {
                            "bulkUpdateFigures": {
                                "errors": [
                                    [
                                        {
                                            "field": "geoLocations",
                                            "messages": f"{expected_match}: cn should be np",
                                        }
                                    ]
                                ],
                                "result": [None],
                            }
                        },
                        None,
                    )
            return responder(query, variables)

        attachment_patch = _patch_download_file()
        with attachment_patch, patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _gql_response
            MockClient.return_value.__enter__.return_value = mock_client
            HulkBulkImportHandler(bulk).handle()

        bulk.refresh_from_db()
        failure_uuids_to_messages = {r["uuid"]: r["error"] for r in _jsonl_rows(_failure_file(bulk, "figures"))}
        # The single post-error row is bad_country.
        self.assertIn(F["bad_country"], failure_uuids_to_messages)
        self.assertIn(
            expected_match,
            json.dumps(failure_uuids_to_messages[F["bad_country"]], default=str),
        )
        # Pre-error (missing_event) still lands in failure with its own substring.
        self.assertIn(F["missing_event"], failure_uuids_to_messages)
        self.assertIn(
            EXPECTED_OUTCOMES["figures"][F["missing_event"]]["error_match"],
            json.dumps(failure_uuids_to_messages[F["missing_event"]], default=str),
        )

    def test_unexpected_event_mutation_response_records_post_error_per_row(self):
        """
        Regression: if ``createEvent`` returns an empty payload (no
        ``createEvent`` key, so parser_fn → None), the row must land as a
        post-error rather than raising KeyError out of
        ``graphql_response_parser_error({})`` and killing the whole run.
        """
        bulk = self._make_bulk_import_with_inputs()
        responder = _CountingResponder()

        def _gql_response(query, variables):
            if "createEvent" in query:
                return ({}, None)
            return responder(query, variables)

        attachment_patch = _patch_download_file()
        with attachment_patch, patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _gql_response
            MockClient.return_value.__enter__.return_value = mock_client
            ok = HulkBulkImportHandler(bulk).handle()

        self.assertTrue(ok)
        bulk.refresh_from_db()
        self.assertEqual(bulk.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)

        event_attempted = {r["uuid"] for r in read_expected_input_rows("events")} - PYDANTIC_ONLY_FAILURE_UUIDS["events"]
        self.assertGreater(len(event_attempted), 0)
        failure_events = {r["uuid"]: r["error"] for r in _jsonl_rows(_failure_file(bulk, "events"))}
        for u in event_attempted:
            self.assertIn(u, failure_events)
            self.assertIn("post-errors", failure_events[u])
            self.assertIn("unexpected mutation response", str(failure_events[u]["post-errors"]))

    def test_figure_mutation_response_empty_records_post_error(self):
        """
        Regression: if ``bulkUpdateFigures`` returns an empty payload (no
        ``bulkUpdateFigures`` key, so parser_fn → None), the figure handler
        must produce a post-error rather than letting
        ``graphql_response_parser_error`` raise IndexError out of
        ``{}["errors"][0]``.
        """
        from apps.hulk.tests.fixtures import FIGURE_UUIDS as F

        bulk = self._make_bulk_import_with_inputs()
        responder = _CountingResponder()
        figure_uuid = F["person_null_hh"]

        def _gql_response(query, variables):
            if "bulkUpdateFigures" in query:
                if (variables.get("input") or {}).get("uuid") == figure_uuid:
                    # parser_fn → None; pre-fix this used to flow into
                    # graphql_response_parser_error({}) → {}["errors"][0].
                    return ({}, None)
            return responder(query, variables)

        attachment_patch = _patch_download_file()
        with attachment_patch, patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _gql_response
            MockClient.return_value.__enter__.return_value = mock_client
            ok = HulkBulkImportHandler(bulk).handle()

        self.assertTrue(ok)
        bulk.refresh_from_db()
        failure_figures = {r["uuid"]: r["error"] for r in _jsonl_rows(_failure_file(bulk, "figures"))}
        self.assertIn(figure_uuid, failure_figures)
        self.assertIn("post-errors", failure_figures[figure_uuid])

    def test_relation_insert_failure_rolls_back_helix_entity(self):
        """
        Review #6 regression: if the per-row ``HulkEntityRelation.create``
        raises after ``_create_entity`` already wrote the helix row, the
        ``transaction.atomic`` block in ``handle_row`` must roll the helix
        row back so no orphan is left for a replay to duplicate.
        """
        from apps.event.models import Event
        from apps.hulk.models import HulkEvent

        bulk = HulkBulkImport.objects.create(created_by=self.user)
        bundle = build_jsonl_bundle(self.ctx)
        _create_dataset(bulk, "events", bundle["events"])

        pre_event_count = Event.objects.count()

        with patch.object(
            HulkEvent.objects,
            "create",
            side_effect=IntegrityError("simulated relation insert failure"),
        ), patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _CountingResponder()
            MockClient.return_value.__enter__.return_value = mock_client
            HulkBulkImportHandler(bulk).handle()

        bulk.refresh_from_db()

        # No helix Event row should have been created: every mutation-attempted
        # row had its factory-created Event rolled back by the atomic block when
        # the patched relation .create raised.
        self.assertEqual(Event.objects.count(), pre_event_count)
        # No HulkEvent relation rows either.
        self.assertEqual(HulkEvent.objects.filter(bulk_import=bulk).count(), 0)

        failure_events = _jsonl_rows(_failure_file(bulk, "events"))
        attempted_mutation_uuids = {r["uuid"] for r in read_expected_input_rows("events")} - PYDANTIC_ONLY_FAILURE_UUIDS[
            "events"
        ]
        self.assertGreater(len(attempted_mutation_uuids), 0)
        post_error_uuids = {
            r["uuid"]
            for r in failure_events
            if isinstance(r["error"].get("post-errors"), str) and "relation insert failed" in r["error"]["post-errors"]
        }
        self.assertEqual(post_error_uuids, attempted_mutation_uuids)

    def test_same_url_source_previews_do_not_collide_on_entity(self):
        """
        Regression: two source_preview rows sharing the same url (distinct
        uuids) must both import successfully, each backed by its OWN SourcePreview
        entity, so the OneToOne unique on ``HulkSourcePreview.entity_id`` holds and
        a downstream URL entry referencing the SECOND uuid still resolves.

        The responder below mimics the real ``SourcePreviewSerializer.create``
        reuse rule (same url → same entity id) UNLESS the mutation input carries
        ``skipRecentReuse: True`` — which is exactly what the hulk source_preview
        path now sends. Under the old behavior (reuse) the second HulkSourcePreview
        insert collided on entity_id → IntegrityError → the second uuid never got a
        relation row → the entry referencing it failed "Unknown source_preview".
        """
        from apps.contrib.models import SourcePreview
        from apps.hulk.models import HulkSourcePreview
        from utils.factories import EntryFactory

        uuid_a = "11111111-1111-1111-1111-111111111111"
        uuid_b = "22222222-2222-2222-2222-222222222222"
        entry_uuid = "33333333-3333-3333-3333-333333333333"
        shared_url = "https://example.com/shared-page"

        source_preview_rows = [
            {"uuid": uuid_a, "file_url": shared_url},
            {"uuid": uuid_b, "file_url": shared_url},
        ]
        # URL entry that points at the SECOND source_preview uuid — this is the
        # link that used to cascade-fail when uuid_b had no HulkSourcePreview row.
        entry_rows = [
            {
                "uuid": entry_uuid,
                "hulk_import_type": "URL",
                "attachment_uuid": None,
                "source_preview_uuid": uuid_b,
                "url": shared_url,
                "entry_title": "URL entry on shared preview",
                "publish_date": "2024-01-15",
                "is_confidential": False,
                "publishers_id": [str(self.ctx["publisher_id"])],
            },
        ]

        bulk = HulkBulkImport.objects.create(created_by=self.user)
        _create_dataset(bulk, "source_previews", dump_jsonl(source_preview_rows))
        _create_dataset(bulk, "entries", dump_jsonl(entry_rows))

        class _ReuseAwareResponder:
            """Reproduces the serializer's url-based reuse unless skipRecentReuse=True."""

            def __init__(self):
                self._entry_factory = EntryFactory
                # url -> entity id, for in-progress previews (mirrors the serializer).
                self._preview_by_url: dict[str, int] = {}

            def __call__(self, query, variables):
                if "createSourcePreview" in query:
                    inp = variables["input"]
                    url = inp.get("url")
                    skip_recent_reuse = inp.get("skipRecentReuse", False)
                    if not skip_recent_reuse and url in self._preview_by_url:
                        pk = self._preview_by_url[url]
                    else:
                        pk = SourcePreview.objects.create(url=url).pk
                        self._preview_by_url[url] = pk
                    return ({"createSourcePreview": {"ok": True, "errors": None, "result": {"id": pk}}}, None)
                if "createEntry" in query:
                    obj = self._entry_factory.create()
                    return ({"createEntry": {"ok": True, "errors": None, "result": {"id": obj.pk}}}, None)
                return ({}, None)

        with patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _ReuseAwareResponder()
            MockClient.return_value.__enter__.return_value = mock_client
            HulkBulkImportHandler(bulk).handle()

        bulk.refresh_from_db()
        self.assertEqual(bulk.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)

        # Both source_preview uuids succeeded, each with a distinct entity.
        sp_success = {r["uuid"]: r for r in _jsonl_rows(_success_file(bulk, "source_previews"))}
        sp_failure = _jsonl_rows(_failure_file(bulk, "source_previews"))
        self.assertEqual(set(sp_success), {uuid_a, uuid_b}, sp_failure)
        self.assertEqual(sp_failure, [])
        self.assertNotEqual(
            sp_success[uuid_a]["id"],
            sp_success[uuid_b]["id"],
            "each same-url row must get its own SourcePreview entity",
        )

        # Two relation rows, two entities — the OneToOne held.
        self.assertEqual(HulkSourcePreview.objects.filter(bulk_import=bulk).count(), 2)
        self.assertEqual(
            HulkSourcePreview.objects.filter(bulk_import=bulk).values_list("entity_id", flat=True).distinct().count(),
            2,
        )

        # The dependent URL entry (referencing uuid_b) resolved and imported —
        # no "Unknown source_preview" cascade.
        entry_success = {r["uuid"] for r in _jsonl_rows(_success_file(bulk, "entries"))}
        entry_failure = _jsonl_rows(_failure_file(bulk, "entries"))
        self.assertIn(entry_uuid, entry_success, entry_failure)
        self.assertEqual(entry_failure, [])

    def test_handle_failed_status_on_exception(self):
        """If anything in process() raises, status flips to FAILED."""
        bulk = self._make_bulk_import_with_inputs()

        with patch(
            "apps.hulk.bulk.handler.HulkBulkImportHandler.process",
            side_effect=RuntimeError("boom"),
        ):
            ok = HulkBulkImportHandler(bulk).handle()

        self.assertFalse(ok)
        bulk.refresh_from_db()
        self.assertEqual(
            bulk.status,
            HulkBulkImport.HULK_BULK_IMPORT_STATUS.FAILED,
        )

    def test_handle_skips_when_status_not_pending(self):
        """CAS guard: handle() must bail if the row is not PENDING.

        Protects against retries / accidental re-dispatch / two workers
        grabbing the same row — only the worker that flips PENDING -> IN_PROGRESS
        is allowed to do the work.
        """
        bulk = self._make_bulk_import_with_inputs()
        bulk.status = HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED
        bulk.save(update_fields=["status"])

        with patch(
            "apps.hulk.bulk.handler.HulkBulkImportHandler.process",
        ) as mock_process:
            ok = HulkBulkImportHandler(bulk).handle()

        self.assertFalse(ok)
        mock_process.assert_not_called()
        bulk.refresh_from_db()
        # Status is unchanged — the CAS refused to transition it.
        self.assertEqual(
            bulk.status,
            HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED,
        )

    def test_handle_partial_inputs(self):
        """A bundle containing only events should not touch the other resources."""
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        bundle = build_jsonl_bundle(self.ctx)
        _create_dataset(bulk, "events", bundle["events"])

        with patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _CountingResponder()
            MockClient.return_value.__enter__.return_value = mock_client
            HulkBulkImportHandler(bulk).handle()

        bulk.refresh_from_db()
        self.assertEqual(bulk.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)
        # Only the events dataset row exists; the four absent resources don't
        # produce dataset rows at all.
        self.assertTrue(bool(_success_file(bulk, "events")))
        for resource in ("attachments", "source_previews", "entries", "figures"):
            with self.subTest(resource=resource):
                self.assertFalse(bulk.datasets.filter(import_type=_TYPE_FOR_RESOURCE[resource].value).exists())
        # Aggregate success_count covers only the events dataset.
        self.assertEqual(_aggregate_counts(bulk)[0], len(_jsonl_rows(_success_file(bulk, "events"))))

    def test_handle_malformed_jsonl_line_records_pre_error(self):
        """
        Regression: a single unparseable JSONL line must not abort the import.
        It lands as a row-level pre-error tagged with the line number, the
        rest of the file (and other resources) keep importing, and the run
        completes successfully.
        """
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        bundle = build_jsonl_bundle(self.ctx)

        # Inject a malformed line at the top of the events dataset; the rest
        # of the bundle is untouched.
        bad_events = b"{not json\n" + bundle["events"]
        _create_dataset(bulk, "events", bad_events)

        with patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _CountingResponder()
            MockClient.return_value.__enter__.return_value = mock_client
            ok = HulkBulkImportHandler(bulk).handle()

        self.assertTrue(ok)
        bulk.refresh_from_db()
        self.assertEqual(bulk.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)

        # Malformed-line marker recorded as a pre-error with no uuid.
        failure_events = _jsonl_rows(_failure_file(bulk, "events"))
        malformed = [r for r in failure_events if r["uuid"] is None]
        self.assertEqual(len(malformed), 1)
        self.assertIn("pre-errors", malformed[0]["error"])
        self.assertIn("malformed jsonl at line 1", malformed[0]["error"]["pre-errors"])

        # The rest of the events file still imported — every fixture-row uuid
        # landed somewhere (success or per-row failure), just like the no-bad-
        # line case.
        all_event_uuids = {r["uuid"] for r in read_expected_input_rows("events")}
        success_uuids = {r["uuid"] for r in _jsonl_rows(_success_file(bulk, "events"))}
        per_row_failure_uuids = {r["uuid"] for r in failure_events if r["uuid"] is not None}
        self.assertEqual(success_uuids | per_row_failure_uuids, all_event_uuids)

    def test_handle_no_inputs_at_all(self):
        """
        Edge case: serializer rejects this end-to-end, but the handler itself
        must cope with all five fields being empty (defence-in-depth).
        """
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        with patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient:
            MockClient.return_value.__enter__.return_value = MagicMock()
            ok = HulkBulkImportHandler(bulk).handle()
        bulk.refresh_from_db()
        self.assertTrue(ok)
        self.assertEqual(bulk.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)
        self.assertEqual(_aggregate_counts(bulk)[0], 0)
        self.assertEqual(_aggregate_counts(bulk)[1], 0)

    def test_handle_figures_without_entries_cascade_pre_errors(self):
        """
        Upload events + figures but no attachments / source_previews / entries.
        Every figure references an entry_uuid that has no HulkEntry row, so
        pyhelix's parse_entry validator should reject all of them with a
        pre-error ("Unknown entry"). missing_event still pre-errors on the
        event side. Nothing lands in success_figures.
        """
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        bundle = build_jsonl_bundle(self.ctx)
        _create_dataset(bulk, "events", bundle["events"])
        _create_dataset(bulk, "figures", bundle["figures"])
        bulk.save()

        with patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _CountingResponder()
            MockClient.return_value.__enter__.return_value = mock_client
            HulkBulkImportHandler(bulk).handle()

        bulk.refresh_from_db()
        self.assertEqual(bulk.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)

        figure_failure = _jsonl_rows(_failure_file(bulk, "figures"))
        figure_success = _jsonl_rows(_success_file(bulk, "figures"))
        figure_input_uuids = {r["uuid"] for r in read_expected_input_rows("figures")}
        # Every single figure should fail because no HulkEntry rows exist to
        # resolve their entry_uuid references.
        self.assertEqual({r["uuid"] for r in figure_failure}, figure_input_uuids)
        self.assertEqual(figure_success, [])
        # Every failure row carries a pre-errors key (pydantic validation).
        for row in figure_failure:
            self.assertIn("pre-errors", row["error"])

    def test_handle_entries_without_attachments_cascade_pre_errors(self):
        """
        Upload entries (which reference attachment_uuid / source_preview_uuid)
        without the upstream attachment / source_preview resources. Every
        non-bad entry should fail with a pre-error pointing at the missing
        relation table row.
        """
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        bundle = build_jsonl_bundle(self.ctx)
        _create_dataset(bulk, "entries", bundle["entries"])

        with patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _CountingResponder()
            MockClient.return_value.__enter__.return_value = mock_client
            HulkBulkImportHandler(bulk).handle()

        bulk.refresh_from_db()
        entry_failure = _jsonl_rows(_failure_file(bulk, "entries"))
        entry_success = _jsonl_rows(_success_file(bulk, "entries"))
        entry_input_uuids = {r["uuid"] for r in read_expected_input_rows("entries")}
        self.assertEqual({r["uuid"] for r in entry_failure}, entry_input_uuids)
        self.assertEqual(entry_success, [])
        for row in entry_failure:
            self.assertIn("pre-errors", row["error"])

    def test_input_jsonl_matches_expected_files(self):
        """
        Regression guard: the bytes that ``build_jsonl_bundle`` produces for
        each resource (after placeholder substitution is undone for the byte
        comparison) match the committed ``expected/jsonl/<resource>.jsonl``.

        The expected files store the *unsubstituted* rows (with placeholders),
        so we compare the raw xlsx-loaded rows (no substitution) against them.
        """
        from apps.hulk.tests.fixtures import _load_raw

        for resource in RESOURCES:
            with self.subTest(resource=resource):
                raw_rows = _load_raw(resource)
                expected_rows = read_expected_input_rows(resource)
                self.assertEqual(raw_rows, expected_rows)

    def test_expected_success_failure_files_cover_every_input_row(self):
        """
        Invariant: every fixture row appears in exactly one of expected/success
        or expected/failure (no row left unassigned, no duplicates).
        """
        for resource in RESOURCES:
            with self.subTest(resource=resource):
                input_uuids = {r["uuid"] for r in read_expected_input_rows(resource)}
                success_uuids = {r["uuid"] for r in read_expected_success(resource)}
                failure_uuids = {r["uuid"] for r in read_expected_failure(resource)}
                self.assertFalse(success_uuids & failure_uuids, "row in both success and failure")
                self.assertEqual(success_uuids | failure_uuids, input_uuids)

    def test_db_state_after_handler_run(self):
        """
        After a mocked-success run, the entity-relation tables (HulkEntry /
        HulkEvent / HulkFigure / HulkSourcePreview / HulkAttachment) should
        carry one row per success_<resource> uuid, each pointing at a real
        Django row. Acts as our lightweight DB-state snapshot — confirms the
        handler wired the import correctly without needing xlsx report
        snapshots that aren't meaningful at this fixture size.
        """
        from apps.contrib.models import Attachment, SourcePreview
        from apps.entry.models import Entry, Figure
        from apps.event.models import Event
        from apps.hulk.models import (
            HulkAttachment,
            HulkEntry,
            HulkEvent,
            HulkFigure,
            HulkSourcePreview,
        )

        bulk = self._make_bulk_import_with_inputs()
        attachment_patch = _patch_download_file()
        with attachment_patch, patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _CountingResponder()
            MockClient.return_value.__enter__.return_value = mock_client
            HulkBulkImportHandler(bulk).handle()

        relation_table_for = {
            "attachments": (HulkAttachment, Attachment),
            "source_previews": (HulkSourcePreview, SourcePreview),
            "entries": (HulkEntry, Entry),
            "events": (HulkEvent, Event),
            "figures": (HulkFigure, Figure),
        }
        for resource in RESOURCES:
            with self.subTest(resource=resource):
                hulk_cls, entity_cls = relation_table_for[resource]
                success_uuids = {r["uuid"] for r in _jsonl_rows(_success_file(bulk, resource))}
                # Each success uuid has a relation row scoped to this bulk import.
                relation_uuids = set(
                    str(u) for u in hulk_cls.objects.filter(bulk_import=bulk).values_list("uuid", flat=True)
                )
                self.assertEqual(relation_uuids, success_uuids)
                # Each relation row points at a live entity.
                entity_ids = list(hulk_cls.objects.filter(bulk_import=bulk).values_list("entity_id", flat=True))
                self.assertEqual(
                    entity_cls.objects.filter(pk__in=entity_ids).count(),
                    len(entity_ids),
                )

    def test_attachment_handler_uses_real_big_attachment_mutations(self):
        """
        End-to-end check for the attachment handler against the real schema:
          * downloads the file (patched to return a ContentFile)
          * allocates the row with the real ``createBigAttachment`` mutation and
            uploads the bytes to the destination key parsed from its presigned url
          * the real ``markBigAttachmentFileAsUploaded`` reads the stored object
            back, sniffs its mimetype and flips ``is_file_uploaded``
          * HulkAttachment relation is created and the success file lists the
            row with ``message="Created"``.
        ``createAttachment``/``Upload!`` is no longer used by this handler at all.
        """
        from apps.contrib.models import Attachment

        bulk = HulkBulkImport.objects.create(created_by=self.user)
        bundle = build_jsonl_bundle(self.ctx)
        _create_dataset(bulk, "attachments", bundle["attachments"])

        with _patch_download_file():
            HulkBulkImportHandler(bulk).handle()

        bulk.refresh_from_db()
        self.assertEqual(bulk.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)
        success_rows = _jsonl_rows(_success_file(bulk, "attachments"))
        self.assertEqual(len(success_rows), len(read_expected_input_rows("attachments")))
        # Each success row points at a real Attachment whose object was uploaded
        # and then verified by markBigAttachmentFileAsUploaded — so the mimetype
        # and size come from the stored bytes, not from the caller.
        for row in success_rows:
            attachment = Attachment.objects.get(pk=row["id"])
            self.assertTrue(bool(attachment.attachment))
            self.assertTrue(attachment.is_file_uploaded)
            self.assertEqual(attachment.mimetype, "application/pdf")
            self.assertTrue(attachment.file_size)
            # Metadata the small-upload serializer used to derive must still be
            # populated now that every row goes through the BigAttachment path.
            self.assertTrue(attachment.encoding)
            self.assertTrue(attachment.filetype_detail)
            self.assertEqual(row["message"], "Created")

    @override_settings(HULK_DIRECT_ACCESS_BUCKETS=["hulk-source"])
    def test_attachment_handler_s3_copy_path_uses_big_attachment_mutations(self):
        """
        When the source ``file_url`` is an AWS S3 URL on a direct-access bucket,
        the handler must move the bytes server-side:

        1. call ``createBigAttachment`` to allocate an Attachment row +
           presigned PUT URL,
        2. parse the presigned URL to extract destination bucket + key,
        3. call ``s3.copy_object`` server-side from the source bucket/key,
        4. call ``markBigAttachmentFileAsUploaded`` to flip the row's
           ``is_file_uploaded=True``.

        Boto3 is mocked end-to-end so this runs without AWS access.
        """
        from apps.contrib.models import Attachment
        from apps.hulk.bulk import handler as handler_mod

        # Fixture rows we'll feed into the bulk import — both file URLs are
        # AWS S3 so both should take the S3-copy path.
        s3_rows = (
            b'{"uuid": "11111111-1111-1111-1111-111111111111", "attachment_for": "ENTRY",'
            b' "file_url": "https://hulk-source.s3.us-east-1.amazonaws.com/inputs/a.pdf"}\n'
            b'{"uuid": "22222222-2222-2222-2222-222222222222", "attachment_for": "ENTRY",'
            b' "file_url": "https://hulk-source.s3.us-east-1.amazonaws.com/inputs/b.pdf"}\n'
        )
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        _create_dataset(bulk, "attachments", s3_rows)

        copy_object_calls = []

        def _fake_run_mutation(query, variables):
            if "createBigAttachment" in query:
                # Create a real Attachment so the relation FK satisfies later.
                obj = Attachment.objects.create(
                    attachment_for=variables["input"]["attachmentFor"],
                    attachment="hulk-dst/" + variables["input"]["fileName"],
                    mimetype=variables["input"]["mimetype"],
                    is_file_uploaded=False,
                )
                return (
                    {
                        "createBigAttachment": {
                            "ok": True,
                            "errors": None,
                            "result": {"id": obj.pk},
                            "s3PresignedUploadUrl": (
                                f"https://helix-dest.s3.us-east-1.amazonaws.com/hulk-dst/"
                                f"{variables['input']['fileName']}?X-Amz-Signature=fake"
                            ),
                        }
                    },
                    None,
                )
            if "markBigAttachmentFileAsUploaded" in query:
                Attachment.objects.filter(pk=variables["id"]).update(is_file_uploaded=True)
                return (
                    {
                        "markBigAttachmentFileAsUploaded": {
                            "ok": True,
                            "errors": None,
                            "result": {"id": variables["id"]},
                        }
                    },
                    None,
                )
            raise AssertionError(f"unexpected mutation: {query!r}")

        fake_s3 = MagicMock()
        fake_s3.copy_object.side_effect = lambda **kwargs: copy_object_calls.append(kwargs)

        with patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient, patch(
            "apps.hulk.bulk.handler.default_storage"
        ) as mock_storage:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _fake_run_mutation
            MockClient.return_value.__enter__.return_value = mock_client
            mock_storage.bucket.meta.client = fake_s3

            handler_mod.HulkBulkImportHandler(bulk).handle()

        bulk.refresh_from_db()
        self.assertEqual(bulk.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)
        success_rows = _jsonl_rows(_success_file(bulk, "attachments"))
        self.assertEqual(len(success_rows), 2)

        # Both rows took the S3 fast path: copy_object was called twice with
        # the source bucket/key from the file_url and the destination bucket/key
        # parsed from the presigned URL.
        self.assertEqual(len(copy_object_calls), 2)
        self.assertEqual(
            {call["CopySource"]["Bucket"] for call in copy_object_calls},
            {"hulk-source"},
        )
        self.assertEqual(
            {call["CopySource"]["Key"] for call in copy_object_calls},
            {"inputs/a.pdf", "inputs/b.pdf"},
        )
        self.assertEqual({call["Bucket"] for call in copy_object_calls}, {"helix-dest"})
        self.assertEqual(
            {call["Key"] for call in copy_object_calls},
            {"hulk-dst/a.pdf", "hulk-dst/b.pdf"},
        )

        # Marked as uploaded by the Mark mutation.
        for row in success_rows:
            attachment = Attachment.objects.get(pk=row["id"])
            self.assertTrue(attachment.is_file_uploaded)

    @override_settings(AWS_S3_ENDPOINT_URL="http://minio:9000", HULK_DIRECT_ACCESS_BUCKETS=[])
    def test_attachment_handler_same_minio_copy_path(self):
        """
        When the source URL points at helix's own MinIO endpoint
        (``settings.AWS_S3_ENDPOINT_URL``), the handler should take the same
        ``s3.copy_object`` fast path it uses for AWS S3 — no httpx download.
        Our own storage needs no ``HULK_DIRECT_ACCESS_BUCKETS`` entry, hence the
        empty override.
        """
        from apps.contrib.models import Attachment
        from apps.hulk.bulk import handler as handler_mod

        minio_row = (
            b'{"uuid": "44444444-4444-4444-4444-444444444444", "attachment_for": "ENTRY",'
            b' "file_url": "http://minio:9000/helix-data/media/old/d.pdf"}\n'
        )
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        _create_dataset(bulk, "attachments", minio_row)

        copy_calls = []

        def _fake_run_mutation(query, variables):
            if "createBigAttachment" in query:
                obj = Attachment.objects.create(
                    attachment_for=variables["input"]["attachmentFor"],
                    attachment="hulk-dst/d.pdf",
                    mimetype=variables["input"]["mimetype"],
                    is_file_uploaded=False,
                )
                return (
                    {
                        "createBigAttachment": {
                            "ok": True,
                            "errors": None,
                            "result": {"id": obj.pk},
                            "s3PresignedUploadUrl": "http://minio:9000/helix-data/hulk-dst/d.pdf?X-Amz-Signature=x",
                        }
                    },
                    None,
                )
            if "markBigAttachmentFileAsUploaded" in query:
                Attachment.objects.filter(pk=variables["id"]).update(is_file_uploaded=True)
                return (
                    {"markBigAttachmentFileAsUploaded": {"ok": True, "errors": None, "result": {"id": variables["id"]}}},
                    None,
                )
            raise AssertionError(f"unexpected mutation: {query!r}")

        fake_s3 = MagicMock()
        fake_s3.copy_object.side_effect = lambda **kw: copy_calls.append(kw)

        with patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient, patch(
            "apps.hulk.bulk.handler.default_storage"
        ) as mock_storage, patch("apps.hulk.bulk.handler.download_file") as mock_download:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _fake_run_mutation
            MockClient.return_value.__enter__.return_value = mock_client
            mock_storage.bucket.meta.client = fake_s3

            handler_mod.HulkBulkImportHandler(bulk).handle()

            mock_download.assert_not_called()

        bulk.refresh_from_db()
        self.assertEqual(bulk.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)
        self.assertEqual(len(copy_calls), 1)
        self.assertEqual(
            copy_calls[0]["CopySource"],
            {"Bucket": "helix-data", "Key": "media/old/d.pdf"},
        )
        self.assertEqual(copy_calls[0]["Bucket"], "helix-data")
        self.assertEqual(copy_calls[0]["Key"], "hulk-dst/d.pdf")

    @override_settings(HULK_DIRECT_ACCESS_BUCKETS=["hulk-source"])
    def test_attachment_handler_s3_copy_path_records_post_error_on_copy_failure(self):
        """If ``s3.copy_object`` raises, the row lands in failure_attachments."""
        from apps.contrib.models import Attachment
        from apps.hulk.bulk import handler as handler_mod

        s3_row = (
            b'{"uuid": "33333333-3333-3333-3333-333333333333", "attachment_for": "ENTRY",'
            b' "file_url": "https://hulk-source.s3.amazonaws.com/inputs/c.pdf"}\n'
        )
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        _create_dataset(bulk, "attachments", s3_row)

        def _fake_run_mutation(query, variables):
            if "createBigAttachment" in query:
                obj = Attachment.objects.create(
                    attachment_for=variables["input"]["attachmentFor"],
                    attachment="hulk-dst/c.pdf",
                    mimetype=variables["input"]["mimetype"],
                    is_file_uploaded=False,
                )
                return (
                    {
                        "createBigAttachment": {
                            "ok": True,
                            "errors": None,
                            "result": {"id": obj.pk},
                            "s3PresignedUploadUrl": ("https://helix-dest.s3.amazonaws.com/hulk-dst/c.pdf"),
                        }
                    },
                    None,
                )
            raise AssertionError(f"unexpected mutation: {query!r}")

        fake_s3 = MagicMock()
        fake_s3.copy_object.side_effect = RuntimeError("AccessDenied")

        with patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient, patch(
            "apps.hulk.bulk.handler.default_storage"
        ) as mock_storage:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _fake_run_mutation
            MockClient.return_value.__enter__.return_value = mock_client
            mock_storage.bucket.meta.client = fake_s3

            handler_mod.HulkBulkImportHandler(bulk).handle()

        bulk.refresh_from_db()
        failure_rows = _jsonl_rows(_failure_file(bulk, "attachments"))
        self.assertEqual(len(failure_rows), 1)
        self.assertIn("post-errors", failure_rows[0]["error"])
        self.assertIn("s3.copy_object failed", str(failure_rows[0]["error"]["post-errors"]))

    @override_settings(HULK_DIRECT_ACCESS_BUCKETS=["direct-bucket"])
    def test_attachment_handler_downloads_s3_url_outside_direct_access_list(self):
        """
        An S3 url whose bucket is not configured for direct access is imported
        the ordinary way: download + re-upload. ``copy_object`` must not be
        attempted — helix's credentials are not meant to be pointed at whatever
        bucket a row happens to name.
        """
        from apps.hulk.bulk import handler as handler_mod

        other_bucket_row = (
            b'{"uuid": "55555555-5555-5555-5555-555555555555", "attachment_for": "ENTRY",'
            b' "file_url": "https://other-bucket.s3.us-east-1.amazonaws.com/inputs/x.pdf"}\n'
        )
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        _create_dataset(bulk, "attachments", other_bucket_row)

        fake_s3 = MagicMock()

        with patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient, patch(
            "apps.hulk.bulk.handler.default_storage"
        ) as mock_storage, _patch_download_file() as mock_download:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _CountingResponder()
            MockClient.return_value.__enter__.return_value = mock_client
            mock_storage.bucket.meta.client = fake_s3

            handler_mod.HulkBulkImportHandler(bulk).handle()

            mock_download.assert_called_once_with("https://other-bucket.s3.us-east-1.amazonaws.com/inputs/x.pdf")

        # Neither the readability probe nor the copy runs for an unlisted bucket.
        fake_s3.head_object.assert_not_called()
        fake_s3.copy_object.assert_not_called()
        # The downloaded bytes are uploaded to the BigAttachment destination key —
        # createAttachment/Upload! is not used for this (or any) row.
        fake_s3.put_object.assert_called_once()
        self.assertEqual(fake_s3.put_object.call_args.kwargs["Body"], _DUMMY_PDF_BYTES)

        bulk.refresh_from_db()
        self.assertEqual(_jsonl_rows(_failure_file(bulk, "attachments")), [])
        self.assertEqual(len(_jsonl_rows(_success_file(bulk, "attachments"))), 1)

    @override_settings(HULK_DIRECT_ACCESS_BUCKETS=["hulk-source"])
    def test_attachment_handler_s3_copy_uses_the_key_candidate_that_exists(self):
        """
        For a key containing a literal ``%``, the decoded reading of the URL
        path points at nothing. The handler must HEAD the candidates and copy
        the one that actually exists instead of decoding blindly.
        """
        from apps.contrib.models import Attachment
        from apps.hulk.bulk import handler as handler_mod

        # Real key: "inputs/report%20final.pdf" (a literal '%20' in the name).
        # The url was built by pasting the raw key in, so decoding gives
        # "inputs/report final.pdf" — which does not exist.
        s3_row = (
            b'{"uuid": "66666666-6666-6666-6666-666666666666", "attachment_for": "ENTRY",'
            b' "file_url": "https://hulk-source.s3.amazonaws.com/inputs/report%20final.pdf"}\n'
        )
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        _create_dataset(bulk, "attachments", s3_row)

        existing_key = "inputs/report%20final.pdf"
        head_keys = []
        copy_calls = []

        def _fake_head_object(*, Bucket, Key):
            head_keys.append(Key)
            if Key != existing_key:
                raise RuntimeError("An error occurred (404) when calling the HeadObject operation: Not Found")
            return {"ContentLength": 10}

        def _fake_run_mutation(query, variables):
            if "createBigAttachment" in query:
                obj = Attachment.objects.create(
                    attachment_for=variables["input"]["attachmentFor"],
                    attachment="hulk-dst/" + variables["input"]["fileName"],
                    mimetype=variables["input"]["mimetype"],
                    is_file_uploaded=False,
                )
                return (
                    {
                        "createBigAttachment": {
                            "ok": True,
                            "errors": None,
                            "result": {"id": obj.pk},
                            "s3PresignedUploadUrl": (
                                "https://helix-dest.s3.amazonaws.com/hulk-dst/report%2520final.pdf?X-Amz-Signature=z"
                            ),
                        }
                    },
                    None,
                )
            if "markBigAttachmentFileAsUploaded" in query:
                Attachment.objects.filter(pk=variables["id"]).update(is_file_uploaded=True)
                return (
                    {"markBigAttachmentFileAsUploaded": {"ok": True, "errors": None, "result": {"id": variables["id"]}}},
                    None,
                )
            raise AssertionError(f"unexpected mutation: {query!r}")

        fake_s3 = MagicMock()
        fake_s3.head_object.side_effect = _fake_head_object
        fake_s3.copy_object.side_effect = lambda **kw: copy_calls.append(kw)

        with patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient, patch(
            "apps.hulk.bulk.handler.default_storage"
        ) as mock_storage, patch("apps.hulk.bulk.handler.download_file") as mock_download:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _fake_run_mutation
            MockClient.return_value.__enter__.return_value = mock_client
            mock_storage.bucket.meta.client = fake_s3

            handler_mod.HulkBulkImportHandler(bulk).handle()

            mock_download.assert_not_called()

        bulk.refresh_from_db()
        self.assertEqual(bulk.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)
        self.assertEqual(len(_jsonl_rows(_success_file(bulk, "attachments"))), 1)
        # Decoded candidate probed first, then the raw one that exists.
        self.assertEqual(head_keys, ["inputs/report final.pdf", existing_key])
        self.assertEqual(len(copy_calls), 1)
        self.assertEqual(copy_calls[0]["CopySource"], {"Bucket": "hulk-source", "Key": existing_key})
        # The destination url is boto3-generated, hence canonically encoded:
        # decoding it exactly once yields the real key.
        self.assertEqual(copy_calls[0]["Key"], "hulk-dst/report%20final.pdf")

    @override_settings(HULK_DIRECT_ACCESS_BUCKETS=["hulk-source"])
    def test_attachment_handler_presigned_source_falls_back_to_signed_download(self):
        """
        A presigned ``file_url`` carries a signature, not credentials, and
        ``copy_object`` cannot present one. So when helix's own credentials
        can't read the object, the handler must download the full signed url and
        upload those bytes, rather than attempt — and fail — a server-side copy.
        """
        from apps.contrib.models import Attachment
        from apps.hulk.bulk import handler as handler_mod

        signed_url = (
            "https://hulk-source.s3.amazonaws.com/inputs/e.pdf"
            "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=deadbeef&X-Amz-Expires=3600"
        )
        s3_row = (
            f'{{"uuid": "77777777-7777-7777-7777-777777777777", "attachment_for": "ENTRY", "file_url": "{signed_url}"}}\n'
        ).encode()
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        _create_dataset(bulk, "attachments", s3_row)

        responder = _CountingResponder()
        mutations_run = []

        def _fake_run_mutation(query, variables):
            mutations_run.append(query)
            return responder(query, variables)

        fake_s3 = MagicMock()
        fake_s3.head_object.side_effect = RuntimeError(
            "An error occurred (403) when calling the HeadObject operation: Forbidden"
        )

        with patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient, patch(
            "apps.hulk.bulk.handler.default_storage"
        ) as mock_storage, _patch_download_file() as mock_download:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _fake_run_mutation
            MockClient.return_value.__enter__.return_value = mock_client
            mock_storage.bucket.meta.client = fake_s3

            handler_mod.HulkBulkImportHandler(bulk).handle()

            # Downloaded through the *full* signed url — dropping the query
            # string would turn this into an unauthenticated 403.
            mock_download.assert_called_once_with(signed_url)

        fake_s3.copy_object.assert_not_called()
        # Signed bytes still land via the BigAttachment sequence, not Upload!.
        fake_s3.put_object.assert_called_once()
        self.assertTrue(any("createBigAttachment" in q for q in mutations_run), mutations_run)
        self.assertFalse(any("createAttachment(" in q for q in mutations_run), mutations_run)

        bulk.refresh_from_db()
        self.assertEqual(bulk.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)
        success_rows = _jsonl_rows(_success_file(bulk, "attachments"))
        self.assertEqual(len(success_rows), 1)
        self.assertTrue(Attachment.objects.filter(pk=success_rows[0]["id"]).exists())

    @override_settings(HULK_DIRECT_ACCESS_BUCKETS=["hulk-source"])
    def test_attachment_handler_unreadable_source_in_direct_bucket_falls_back_to_download(self):
        """
        Being configured for direct access doesn't guarantee a given object is
        readable (wrong key, object ACL, expired role). The probe failing must
        degrade to download+upload — and must do so *before* createBigAttachment
        so no orphan Attachment row is left pointing at an uncopied object.
        """
        from apps.hulk.bulk import handler as handler_mod

        url = "https://hulk-source.s3.amazonaws.com/inputs/missing.pdf"
        s3_row = (
            b'{"uuid": "88888888-8888-8888-8888-888888888888", "attachment_for": "ENTRY",'
            b' "file_url": "' + url.encode() + b'"}\n'
        )
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        _create_dataset(bulk, "attachments", s3_row)

        mutations_run = []

        def _fake_run_mutation(query, variables):
            mutations_run.append(query)
            return _CountingResponder()(query, variables)

        fake_s3 = MagicMock()
        fake_s3.head_object.side_effect = RuntimeError(
            "An error occurred (404) when calling the HeadObject operation: Not Found"
        )

        with patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient, patch(
            "apps.hulk.bulk.handler.default_storage"
        ) as mock_storage, _patch_download_file() as mock_download:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _fake_run_mutation
            MockClient.return_value.__enter__.return_value = mock_client
            mock_storage.bucket.meta.client = fake_s3

            handler_mod.HulkBulkImportHandler(bulk).handle()

            mock_download.assert_called_once_with(url)

        fake_s3.copy_object.assert_not_called()
        # No copy, but the row still goes through createBigAttachment + upload +
        # mark; the probe ran before any mutation, so nothing was left orphaned.
        fake_s3.put_object.assert_called_once()
        self.assertTrue(any("createBigAttachment" in q for q in mutations_run), mutations_run)

        bulk.refresh_from_db()
        self.assertEqual(_jsonl_rows(_failure_file(bulk, "attachments")), [])
        self.assertEqual(len(_jsonl_rows(_success_file(bulk, "attachments"))), 1)

    def test_attachment_handler_download_failure_is_post_error(self):
        """
        If ``download_file`` raises (network / 404 / unsupported chars), the
        row lands in ``failure_attachments`` with a post-error message.
        """
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        bundle = build_jsonl_bundle(self.ctx)
        _create_dataset(bulk, "attachments", bundle["attachments"])

        with patch("apps.hulk.bulk.handler.download_file", side_effect=RuntimeError("boom")):
            HulkBulkImportHandler(bulk).handle()

        bulk.refresh_from_db()
        failure_rows = _jsonl_rows(_failure_file(bulk, "attachments"))
        self.assertEqual(len(failure_rows), len(read_expected_input_rows("attachments")))
        for row in failure_rows:
            self.assertIn("post-errors", row["error"])
            self.assertIn("download failed", row["error"]["post-errors"])


class TestHulkBulkImportImpersonation(HelixGraphQLTestCase):
    """
    Per-row ``impersonate_as`` flow:
      * unset → mutations run as ``bulk_import.created_by``
      * set to a valid active user → mutations run as that user
      * unknown / inactive PK → row pre-errors, mutation never runs
      * cache reuses one login per unique target user across rows
    """

    def setUp(self):
        self.creator = create_user_with_role(USER_ROLE.ADMIN.name)
        self.impersonated = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)

    def _source_preview_rows(self, rows: list[dict]) -> bytes:
        return ("\n".join(json.dumps(r) for r in rows) + "\n").encode("utf-8")

    def _run(self, bulk):
        with patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _CountingResponder()
            MockClient.return_value.__enter__.return_value = mock_client
            HulkBulkImportHandler(bulk).handle()
            return MockClient

    def test_impersonate_uses_specified_user(self):
        bulk = HulkBulkImport.objects.create(created_by=self.creator)
        _create_dataset(
            bulk,
            "source_previews",
            self._source_preview_rows(
                [
                    {
                        "uuid": "11111111-1111-4111-8111-111111111111",
                        "file_url": "https://example.invalid/a.pdf",
                        "impersonate_as": self.impersonated.pk,
                    }
                ]
            ),
        )
        MockClient = self._run(bulk)

        # The cache opens one client and reuses it; for an impersonated-only row
        # the only login should target the impersonated user, not the creator.
        constructed_with = [call.args[0] for call in MockClient.call_args_list]
        self.assertIn(self.impersonated, constructed_with)
        self.assertNotIn(self.creator, constructed_with)

    def test_impersonate_unset_uses_bulk_import_creator(self):
        bulk = HulkBulkImport.objects.create(created_by=self.creator)
        _create_dataset(
            bulk,
            "source_previews",
            self._source_preview_rows(
                [
                    {
                        "uuid": "22222222-2222-4222-8222-222222222222",
                        "file_url": "https://example.invalid/a.pdf",
                    }
                ]
            ),
        )
        MockClient = self._run(bulk)

        constructed_with = [call.args[0] for call in MockClient.call_args_list]
        self.assertEqual(constructed_with, [self.creator])

    def test_impersonate_unknown_user_pre_errors_and_skips_mutation(self):
        bulk = HulkBulkImport.objects.create(created_by=self.creator)
        _create_dataset(
            bulk,
            "source_previews",
            self._source_preview_rows(
                [
                    {
                        "uuid": "33333333-3333-4333-8333-333333333333",
                        "file_url": "https://example.invalid/a.pdf",
                        "impersonate_as": 999_999,
                    }
                ]
            ),
        )
        with patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient:
            mock_client = MagicMock()
            mock_client.run_mutation.side_effect = _CountingResponder()
            MockClient.return_value.__enter__.return_value = mock_client
            HulkBulkImportHandler(bulk).handle()

        bulk.refresh_from_db()
        failure_rows = _jsonl_rows(_failure_file(bulk, "source_previews"))
        self.assertEqual(len(failure_rows), 1)
        self.assertIn("pre-errors", failure_rows[0]["error"])
        self.assertIn("999999", str(failure_rows[0]["error"]["pre-errors"]))
        # Bad impersonation must not trigger any login: a row that pre-errors
        # before _create_entity never reaches the GraphQL client.
        mock_client.run_mutation.assert_not_called()

    def test_impersonate_inactive_user_pre_errors(self):
        self.impersonated.is_active = False
        self.impersonated.save(update_fields=["is_active"])

        bulk = HulkBulkImport.objects.create(created_by=self.creator)
        _create_dataset(
            bulk,
            "source_previews",
            self._source_preview_rows(
                [
                    {
                        "uuid": "44444444-4444-4444-8444-444444444444",
                        "file_url": "https://example.invalid/a.pdf",
                        "impersonate_as": self.impersonated.pk,
                    }
                ]
            ),
        )
        self._run(bulk)

        bulk.refresh_from_db()
        failure_rows = _jsonl_rows(_failure_file(bulk, "source_previews"))
        self.assertEqual(len(failure_rows), 1)
        self.assertIn("pre-errors", failure_rows[0]["error"])

    def test_client_cache_reuses_login_per_user_across_rows(self):
        other = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        bulk = HulkBulkImport.objects.create(created_by=self.creator)
        _create_dataset(
            bulk,
            "source_previews",
            self._source_preview_rows(
                [
                    # 3 rows for impersonated, 2 for `other`, 1 default — 6 rows,
                    # 3 unique users → expect exactly 3 client constructions.
                    {
                        "uuid": "50000000-0000-4000-8000-000000000001",
                        "file_url": "u",
                        "impersonate_as": self.impersonated.pk,
                    },
                    {
                        "uuid": "50000000-0000-4000-8000-000000000002",
                        "file_url": "u",
                        "impersonate_as": self.impersonated.pk,
                    },
                    {
                        "uuid": "50000000-0000-4000-8000-000000000003",
                        "file_url": "u",
                        "impersonate_as": self.impersonated.pk,
                    },
                    {"uuid": "50000000-0000-4000-8000-000000000004", "file_url": "u", "impersonate_as": other.pk},
                    {"uuid": "50000000-0000-4000-8000-000000000005", "file_url": "u", "impersonate_as": other.pk},
                    {"uuid": "50000000-0000-4000-8000-000000000006", "file_url": "u"},
                ]
            ),
        )
        MockClient = self._run(bulk)

        constructed_with = [call.args[0] for call in MockClient.call_args_list]
        # Order isn't guaranteed but the *set* of unique constructions is.
        self.assertEqual(
            {u.pk for u in constructed_with},
            {self.impersonated.pk, other.pk, self.creator.pk},
        )
        self.assertEqual(len(constructed_with), 3)


class TestGraphqlErrorNormalization(HelixGraphQLTestCase):
    """
    graphene returns ``GraphQLLocatedError`` exception objects from
    ``schema.execute(...).errors``. They aren't JSON-serializable, so if they
    leak into ``handler.error_list`` the per-dataset ``failure.jsonl`` write
    blows up in ``_persist_results`` and flips the bulk to FAILED even though
    every row was processed. ``_normalize_graphql_errors`` collapses them to
    ``.formatted`` dicts at the ``_handle_mutation`` boundary.
    """

    def test_normalize_uses_formatted_dict(self):
        class FakeGraphQLError(Exception):
            formatted = {"message": "You do not have permission", "path": ["createSourcePreview"]}

        out = _normalize_graphql_errors([FakeGraphQLError()])
        self.assertEqual(out, [{"message": "You do not have permission", "path": ["createSourcePreview"]}])

    def test_normalize_falls_back_to_str_when_no_formatted(self):
        out = _normalize_graphql_errors([ValueError("boom")])
        self.assertEqual(out, [{"message": "boom"}])

    def test_normalize_none_and_empty(self):
        self.assertIsNone(_normalize_graphql_errors(None))
        self.assertEqual(_normalize_graphql_errors([]), [])

    def test_graphql_error_row_persists_to_failure_jsonl(self):
        """
        Regression: when run_mutation surfaces a ``GraphQLLocatedError``-shaped
        object (e.g. from a permission denial on an impersonated user),
        ``_persist_results`` must successfully write the failure JSONL and the
        bulk must NOT flip to FAILED — the row is a row-level failure, not a
        run-level failure.
        """

        class FakeGraphQLError(Exception):
            def __init__(self, message):
                super().__init__(message)
                self.formatted = {"message": message, "path": ["createSourcePreview"]}

        creator = create_user_with_role(USER_ROLE.ADMIN.name)
        bulk = HulkBulkImport.objects.create(created_by=creator)
        _create_dataset(
            bulk,
            "source_previews",
            (
                "\n".join(
                    json.dumps(r)
                    for r in [
                        {"uuid": "60000000-0000-4000-8000-000000000001", "file_url": "https://x.invalid/a.pdf"},
                    ]
                )
                + "\n"
            ).encode("utf-8"),
        )

        with patch("apps.hulk.bulk.handler.InternalHelixGraphQlClient") as MockClient:
            mock_client = MagicMock()
            mock_client.run_mutation.return_value = (
                {"createSourcePreview": None},
                [FakeGraphQLError("You do not have permission to perform this action.")],
            )
            MockClient.return_value.__enter__.return_value = mock_client
            ok = HulkBulkImportHandler(bulk).handle()

        bulk.refresh_from_db()
        # Bulk should be COMPLETED — the row failed, the run did not.
        self.assertTrue(ok, "handle() should report success even when individual rows fail")
        self.assertEqual(bulk.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)

        failure_rows = _jsonl_rows(_failure_file(bulk, "source_previews"))
        self.assertEqual(len(failure_rows), 1)
        self.assertIn("post-errors", failure_rows[0]["error"])
        self.assertEqual(
            failure_rows[0]["error"]["post-errors"],
            [{"message": "You do not have permission to perform this action.", "path": ["createSourcePreview"]}],
        )
