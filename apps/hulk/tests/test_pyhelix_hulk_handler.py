"""
Tests for ``HulkDataHandler``'s duplicate-uuid reporting.

The handler writes every row it is handed; a repeated uuid within one dataset
is counted in ``debug_metadata()``, listed in ``duplicate_uuids.jsonl`` next to
the per-resource JSONL, and blocks the push to helix.

Nothing here needs the database or a live helix — only the import models that
build without reaching ``get_active_helix_client()`` are used.
"""

from __future__ import annotations

import json
import pathlib
import tempfile
import uuid

from django.test import SimpleTestCase
from pyhelix.hulk import (
    DUPLICATE_UUID_REPORT_NAME,
    DuplicateUuidError,
    HulkBulkImportRun,
    HulkDataHandler,
)
from pyhelix.models import HulkAttachmentImport, HulkSourcePreviewImport

UUID_A = uuid.UUID("00000000-0000-0000-0000-00000000000a")
UUID_B = uuid.UUID("00000000-0000-0000-0000-00000000000b")


def _attachment(row_uuid: uuid.UUID) -> HulkAttachmentImport:
    return HulkAttachmentImport(uuid=row_uuid, file_url="https://example.com/a.pdf")


def _source_preview(row_uuid: uuid.UUID) -> HulkSourcePreviewImport:
    return HulkSourcePreviewImport(uuid=row_uuid, file_url="https://example.com/a.html")


class _DummyHelixClient:
    """
    Stand-in for ``HelixClient``: the handler only binds it into a context and,
    on push, calls ``trigger_hulk_bulk_import``. Calls are recorded so a test can
    tell whether an upload happened.
    """

    BULK_ID = "bulk-1"

    def __init__(self):
        self.triggered = []

    def trigger_hulk_bulk_import(self, paths):
        self.triggered.append(paths)
        return self.BULK_ID


class _HandlerTestCase(SimpleTestCase):
    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.export_dir = pathlib.Path(self._tmp_dir.name)
        self.helix_client = _DummyHelixClient()

    def _handler(self) -> HulkDataHandler:
        return HulkDataHandler(export_dir=self.export_dir, helix_client=self.helix_client)

    def _report_rows(self) -> list:
        report = self.export_dir / DUPLICATE_UUID_REPORT_NAME
        return [json.loads(line) for line in report.read_text().splitlines() if line]


class TestDuplicateUuidReporting(_HandlerTestCase):
    def test_distinct_uuids_in_one_dataset_are_not_reported(self):
        with self._handler() as handler:
            handler.handle_import_object(_attachment(UUID_A))
            handler.handle_import_object(_attachment(UUID_B))
            metadata = handler.debug_metadata()

        self.assertEqual(metadata["count"]["duplicates"], {})
        self.assertEqual(self._report_rows(), [])

    def test_uuid_written_twice_into_one_dataset_is_counted_and_listed(self):
        with self._handler() as handler:
            handler.handle_import_object(_attachment(UUID_A))
            handler.handle_import_object(_attachment(UUID_A))
            metadata = handler.debug_metadata()

        self.assertEqual(metadata["count"]["duplicates"], {"HulkAttachmentImport": 1})
        self.assertEqual(
            self._report_rows(),
            [{"import_type": "HulkAttachmentImport", "uuid": str(UUID_A)}],
        )

    def test_uuids_stay_out_of_the_metadata(self):
        """The report file is the only place the uuid list lives."""
        with self._handler() as handler:
            handler.handle_import_object(_attachment(UUID_A))
            handler.handle_import_object(_attachment(UUID_A))
            metadata = handler.debug_metadata()

        self.assertNotIn(str(UUID_A), json.dumps(metadata))
        self.assertEqual(metadata["files"]["duplicates"], DUPLICATE_UUID_REPORT_NAME)

    def test_count_is_the_number_of_repeat_rows(self):
        """Three rows sharing a uuid are two repeats — the first row is not one."""
        with self._handler() as handler:
            for _ in range(3):
                handler.handle_import_object(_attachment(UUID_A))
            metadata = handler.debug_metadata()

        self.assertEqual(metadata["count"]["duplicates"], {"HulkAttachmentImport": 2})
        self.assertEqual(len(self._report_rows()), 2)
        # Duplicates are reported, not dropped: every row reaches the dataset and counts as a success.
        self.assertEqual(metadata["count"]["success"]["HulkAttachmentImport"], 3)
        self.assertEqual(len((self.export_dir / "attachments.jsonl").read_text().splitlines()), 3)

    def test_same_uuid_across_two_datasets_is_not_a_duplicate(self):
        """A row and the row referencing it legitimately share one uuid."""
        with self._handler() as handler:
            handler.handle_import_object(_attachment(UUID_A))
            handler.handle_import_object(_source_preview(UUID_A))
            metadata = handler.debug_metadata()

        self.assertEqual(metadata["count"]["duplicates"], {})
        self.assertEqual(self._report_rows(), [])

    def test_each_dataset_reports_its_own_duplicates(self):
        with self._handler() as handler:
            handler.handle_import_object(_attachment(UUID_A))
            handler.handle_import_object(_attachment(UUID_A))
            handler.handle_import_object(_attachment(UUID_B))
            handler.handle_import_object(_source_preview(UUID_B))
            handler.handle_import_object(_source_preview(UUID_B))
            handler.handle_import_object(_source_preview(UUID_B))
            metadata = handler.debug_metadata()

        self.assertEqual(
            metadata["count"]["duplicates"],
            {"HulkAttachmentImport": 1, "HulkSourcePreviewImport": 2},
        )
        self.assertEqual(
            self._report_rows(),
            [
                {"import_type": "HulkAttachmentImport", "uuid": str(UUID_A)},
                {"import_type": "HulkSourcePreviewImport", "uuid": str(UUID_B)},
                {"import_type": "HulkSourcePreviewImport", "uuid": str(UUID_B)},
            ],
        )


class TestSendToHelixDuplicateGuard(_HandlerTestCase):
    def test_duplicates_block_the_upload(self):
        with self._handler() as handler:
            handler.handle_import_object(_attachment(UUID_A))
            handler.handle_import_object(_attachment(UUID_A))

            with self.assertRaises(DuplicateUuidError) as cm:
                handler.send_to_helix()

        message = str(cm.exception)
        self.assertIn("HulkAttachmentImport: 1", message)
        self.assertIn(str(self.export_dir / DUPLICATE_UUID_REPORT_NAME), message)
        self.assertEqual(self.helix_client.triggered, [])

    def test_the_message_names_the_file_instead_of_the_uuids(self):
        with self._handler() as handler:
            for row_uuid in (UUID_A, UUID_A, UUID_B, UUID_B):
                handler.handle_import_object(_attachment(row_uuid))

            with self.assertRaises(DuplicateUuidError) as cm:
                handler.send_to_helix()

        message = str(cm.exception)
        self.assertNotIn(str(UUID_A), message)
        self.assertNotIn(str(UUID_B), message)

    def test_the_report_is_readable_while_still_inside_the_context(self):
        """send_to_helix flushes the writer, so the named path is complete."""
        with self._handler() as handler:
            handler.handle_import_object(_attachment(UUID_A))
            handler.handle_import_object(_attachment(UUID_A))

            with self.assertRaises(DuplicateUuidError):
                handler.send_to_helix()

            self.assertEqual(
                self._report_rows(),
                [{"import_type": "HulkAttachmentImport", "uuid": str(UUID_A)}],
            )

    def test_clean_datasets_are_uploaded(self):
        with self._handler() as handler:
            handler.handle_import_object(_attachment(UUID_A))
            handler.handle_import_object(_attachment(UUID_B))

            run = handler.send_to_helix()

        self.assertIsInstance(run, HulkBulkImportRun)
        self.assertEqual(run.bulk_id, _DummyHelixClient.BULK_ID)
        self.assertEqual(len(self.helix_client.triggered), 1)
        self.assertEqual(sorted(self.helix_client.triggered[0]), ["attachments"])
