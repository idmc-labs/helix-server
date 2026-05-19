"""
Golden-file regression test for the helix rows the hulk handler creates.

Runs the canonical fixture end-to-end against the *real* helix schema
(``createAttachment`` / ``createSourcePreview`` / ``createEntry`` /
``createEvent`` / ``bulkUpdateFigures``) — only ``download_file`` and the
async PDF render path are stubbed. The resulting Entry / Event / Figure /
Attachment / SourcePreview rows are dumped via ``dump_db_state`` and
bit-compared against ``artifacts/fixtures/hulk-bulk/expected/db-state.json``.

Regenerate the golden after an intentional behaviour change with::

    HULK_UPDATE_DB_SNAPSHOT=1 pytest apps/hulk/tests/test_db_state_snapshot.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.contrib.models import SourcePreview
from apps.hulk.bulk.db_snapshot import dump_db_state
from apps.hulk.bulk.handler import HulkBulkImportHandler
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

from .fixtures import FixtureContext, build_jsonl_bundle

GOLDEN_PATH = Path(__file__).resolve().parents[3] / "artifacts" / "fixtures" / "hulk-bulk" / "expected" / "db-state.json"

# Same minimal PDF the dummy seeder uses — libmagic recognises it as
# application/pdf even after gzip-on-storage thanks to the
# verify_uploaded decompression path.
_DUMMY_PDF_BYTES = (
    b"%PDF-1.1\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 99 99]/Parent 2 0 R/Resources<<>>>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n164\n%%EOF\n"
)


def _make_ctx() -> FixtureContext:
    return FixtureContext(
        country_id=CountryFactory.create(iso2="NP", iso3="NPL", idmc_short_name="Nepal").id,
        publisher_id=OrganizationFactory.create(name="Test Publisher").id,
        source_id=OrganizationFactory.create(name="Test Source").id,
        violence_sub_type_id=ViolenceSubTypeFactory.create(name="Test Violence").id,
        disaster_sub_type_id=DisasterSubTypeFactory.create(name="Test Disaster").id,
        other_sub_type_id=OtherSubtypeFactory.create(name="Test Other").id,
    )


def _fake_download(_url):
    return SimpleUploadedFile(
        name="dummy.pdf",
        content=_DUMMY_PDF_BYTES,
        content_type="application/pdf",
    )


def _stub_get_pdf(validated_data, instance=None):
    """
    Bypass the async PDF render: return (or update) a SourcePreview row in
    COMPLETED state with the requested URL. Mirrors the shape
    ``SourcePreview.get_pdf`` returns under happy-path render.
    """
    if instance is None:
        instance = SourcePreview.objects.create(
            url=validated_data["url"],
            status=SourcePreview.PREVIEW_STATUS.COMPLETED,
        )
    else:
        instance.url = validated_data["url"]
        instance.status = SourcePreview.PREVIEW_STATUS.COMPLETED
        instance.save()
    return instance


# Short resource name → HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE member.
_TYPE_FOR_RESOURCE = {
    "attachments": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.ATTACHMENT,
    "source_previews": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.SOURCE_PREVIEW,
    "entries": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.ENTRY,
    "events": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.EVENT,
    "figures": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.FIGURE,
}


class TestHulkDbStateSnapshot(HelixGraphQLTestCase):
    """
    Single end-to-end test that's also the snapshot generator. Set
    ``HULK_UPDATE_DB_SNAPSHOT=1`` in the environment to overwrite the
    golden file instead of asserting against it.
    """

    def setUp(self):
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.ctx = _make_ctx()
        self.bundle = build_jsonl_bundle(self.ctx)

    def _run_handler(self) -> HulkBulkImport:
        bulk = HulkBulkImport.objects.create(created_by=self.user)
        for resource, payload in self.bundle.items():
            ds = HulkBulkImportDataset.objects.create(
                bulk_import=bulk,
                import_type=_TYPE_FOR_RESOURCE[resource].value,
            )
            ds.import_file.save(f"{resource}.jsonl", ContentFile(payload), save=True)

        # Patch the only two external integrations the handler hits.
        with patch("apps.hulk.bulk.handler.download_file", side_effect=_fake_download), patch(
            "apps.contrib.models.SourcePreview.get_pdf", side_effect=_stub_get_pdf
        ):
            HulkBulkImportHandler(bulk).handle()
        return bulk

    def test_db_state_matches_golden(self):
        bulk = self._run_handler()
        snapshot = dump_db_state(bulk)
        serialised = json.dumps(snapshot, indent=2, sort_keys=True, default=str) + "\n"

        if os.environ.get("HULK_UPDATE_DB_SNAPSHOT") == "1":
            GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            GOLDEN_PATH.write_text(serialised)
            self.skipTest(f"Wrote new db-state golden to {GOLDEN_PATH}. Re-run without HULK_UPDATE_DB_SNAPSHOT to verify.")
            return

        self.assertTrue(
            GOLDEN_PATH.exists(),
            f"Missing golden {GOLDEN_PATH}; regenerate with HULK_UPDATE_DB_SNAPSHOT=1.",
        )
        expected = GOLDEN_PATH.read_text()
        self.assertEqual(
            serialised,
            expected,
            f"Hulk handler DB state drifted from {GOLDEN_PATH.name}. "
            "If the change is intentional, regenerate with "
            "HULK_UPDATE_DB_SNAPSHOT=1.",
        )
