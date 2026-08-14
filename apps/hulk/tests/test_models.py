"""
Model-layer tests for ``HulkBulkImport`` + ``HulkBulkImportDataset``: dataset
rows persist their four file artifacts and the ``update_status`` state
machine sets + saves timestamps.
"""

from __future__ import annotations

from django.core.files.base import ContentFile
from django.db import IntegrityError

from apps.hulk.models import HULK_BULK_RESOURCES, HulkBulkImport, HulkBulkImportDataset
from apps.users.enums import USER_ROLE
from utils.tests import HelixGraphQLTestCase, create_user_with_role

# Short resource name → HULK_BULK_IMPORT_DATASET_IMPORT_TYPE enum member.
_TYPE_FOR_RESOURCE = {
    "attachments": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.ATTACHMENT,
    "source_previews": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.SOURCE_PREVIEW,
    "entries": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.ENTRY,
    "events": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.EVENT,
    "figures": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.FIGURE,
}


class TestHulkBulkImportModel(HelixGraphQLTestCase):
    def setUp(self):
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)

    def test_dataset_import_file_round_trip(self):
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        for resource in HULK_BULK_RESOURCES:
            ds = HulkBulkImportDataset.objects.create(
                bulk_import=bulk,
                import_type=_TYPE_FOR_RESOURCE[resource].value,
            )
            ds.import_file.save(f"{resource}.jsonl", ContentFile(b'{"uuid": "x"}\n'), save=True)

        bulk.refresh_from_db()
        self.assertEqual(bulk.datasets.count(), len(HULK_BULK_RESOURCES))
        for ds in bulk.datasets.all():
            with self.subTest(import_type=ds.get_import_type_display()):
                self.assertTrue(bool(ds.import_file))
                self.assertFalse(bool(ds.success_file))
                self.assertFalse(bool(ds.failure_file))
                self.assertFalse(bool(ds.skip_file))

    def test_dataset_success_failure_skip_round_trip(self):
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        ds = HulkBulkImportDataset.objects.create(
            bulk_import=bulk,
            import_type=HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.ENTRY.value,
        )
        ds.import_file.save("entries.jsonl", ContentFile(b'{"uuid": "x"}\n'), save=False)
        ds.success_file.save(
            "success.jsonl",
            ContentFile(b'{"uuid":"a","id":1,"message":"ok"}\n'),
            save=False,
        )
        ds.failure_file.save(
            "failure.jsonl",
            ContentFile(b'{"uuid":"b","error":{"pre-errors":"x"}}\n'),
            save=False,
        )
        ds.skip_file.save(
            "skip.jsonl",
            ContentFile(b'{"uuid":"c","id":2,"message":"Already exists"}\n'),
            save=False,
        )
        ds.success_count = 1
        ds.failure_count = 1
        ds.skip_count = 1
        ds.save()

        ds.refresh_from_db()
        self.assertTrue(bool(ds.import_file))
        self.assertTrue(bool(ds.success_file))
        self.assertTrue(bool(ds.failure_file))
        self.assertTrue(bool(ds.skip_file))
        self.assertEqual(ds.success_count, 1)
        self.assertEqual(ds.failure_count, 1)
        self.assertEqual(ds.skip_count, 1)

    def test_dataset_unique_per_import_type(self):
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        HulkBulkImportDataset.objects.create(
            bulk_import=bulk,
            import_type=HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.ENTRY.value,
        )
        with self.assertRaises(IntegrityError):
            HulkBulkImportDataset.objects.create(
                bulk_import=bulk,
                import_type=HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.ENTRY.value,
            )

    def test_update_status_sets_and_persists_started_at(self):
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        self.assertIsNone(bulk.started_at)
        bulk.update_status(HulkBulkImport.HULK_BULK_IMPORT_STATUS.IN_PROGRESS)
        bulk.refresh_from_db()
        self.assertEqual(bulk.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.IN_PROGRESS)
        self.assertIsNotNone(bulk.started_at)
        self.assertIsNone(bulk.completed_at)

    def test_update_status_sets_completed_at_on_terminal(self):
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        bulk.update_status(HulkBulkImport.HULK_BULK_IMPORT_STATUS.IN_PROGRESS)
        bulk.update_status(HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)
        bulk.refresh_from_db()
        self.assertEqual(bulk.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)
        self.assertIsNotNone(bulk.completed_at)

    def test_update_status_failed_also_completes(self):
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        bulk.update_status(HulkBulkImport.HULK_BULK_IMPORT_STATUS.FAILED)
        bulk.refresh_from_db()
        self.assertEqual(bulk.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.FAILED)
        self.assertIsNotNone(bulk.completed_at)
