from unittest.mock import patch

from django.conf import settings
from django.test import RequestFactory
from django.utils import timezone

from apps.contrib.models import ExcelDownload, SourcePreview
from apps.contrib.serializers import ExcelDownloadSerializer, SourcePreviewSerializer
from apps.users.enums import USER_ROLE
from utils.tests import HelixTestCase, create_user_with_role


class TestExcelDownload(HelixTestCase):
    def setUp(self) -> None:
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.request = RequestFactory().post("/graphql")
        self.context = {}

    def test_valid_excel_export_if_all_complete(self):
        self.request.user = self.admin
        self.context["request"] = self.request
        ExcelDownload.objects.create(
            started_at=timezone.now(),
            completed_at=timezone.now(),
            download_type=ExcelDownload.DOWNLOAD_TYPES.ENTRY,
            status=ExcelDownload.EXCEL_GENERATION_STATUS.COMPLETED,
            created_by=self.admin,
        )
        ExcelDownload.objects.create(
            started_at=timezone.now(),
            completed_at=timezone.now(),
            download_type=ExcelDownload.DOWNLOAD_TYPES.ENTRY,
            status=ExcelDownload.EXCEL_GENERATION_STATUS.FAILED,
        )

        serializer = ExcelDownloadSerializer(
            data=dict(
                download_type=ExcelDownload.DOWNLOAD_TYPES.ENTRY.value,
                filters={},
            ),
            context=self.context,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_excel_export_if_in_progress_beyond_limit(self):
        self.request.user = self.admin
        self.context["request"] = self.request
        downloads = []
        for _ in range(settings.EXCEL_EXPORT_CONCURRENT_DOWNLOAD_LIMIT):
            downloads.append(
                ExcelDownload.objects.create(
                    started_at=timezone.now(),
                    completed_at=timezone.now(),
                    download_type=ExcelDownload.DOWNLOAD_TYPES.ENTRY,
                    status=ExcelDownload.EXCEL_GENERATION_STATUS.PENDING,
                    created_by=self.admin,
                )
            )
        excel_download = downloads[-1]

        # checking for pending only
        serializer = ExcelDownloadSerializer(
            data=dict(
                download_type=ExcelDownload.DOWNLOAD_TYPES.ENTRY.value,
                filters={},
            ),
            context=self.context,
        )
        self.assertFalse(serializer.is_valid())

        excel_download.delete()
        excel_download = ExcelDownload.objects.create(
            started_at=timezone.now(),
            completed_at=timezone.now(),
            download_type=ExcelDownload.DOWNLOAD_TYPES.ENTRY,
            status=ExcelDownload.EXCEL_GENERATION_STATUS.IN_PROGRESS,
            created_by=self.admin,
        )

        # checking with in_progress as well
        serializer = ExcelDownloadSerializer(
            data=dict(
                download_type=ExcelDownload.DOWNLOAD_TYPES.ENTRY.value,
                filters={},
            ),
            context=self.context,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)
        self.assertEqual("limited-at-a-time", serializer.errors["non_field_errors"][0].code)

        excel_download.delete()
        # failed downloads are allowed though
        excel_download = ExcelDownload.objects.create(
            started_at=timezone.now(),
            completed_at=timezone.now(),
            download_type=ExcelDownload.DOWNLOAD_TYPES.ENTRY,
            status=ExcelDownload.EXCEL_GENERATION_STATUS.FAILED,
            created_by=self.admin,
        )

        serializer = ExcelDownloadSerializer(
            data=dict(
                download_type=ExcelDownload.DOWNLOAD_TYPES.ENTRY.value,
                filters={},
            ),
            context=self.context,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        # other user downloads dont matter
        other_user = create_user_with_role(USER_ROLE.ADMIN.name)
        ExcelDownload.objects.create(
            started_at=timezone.now(),
            completed_at=timezone.now(),
            download_type=ExcelDownload.DOWNLOAD_TYPES.ENTRY,
            status=ExcelDownload.EXCEL_GENERATION_STATUS.IN_PROGRESS,
            created_by=other_user,
        )

        serializer = ExcelDownloadSerializer(
            data=dict(
                download_type=ExcelDownload.DOWNLOAD_TYPES.ENTRY.value,
                filters={},
            ),
            context=self.context,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)


class TestSourcePreviewSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.request = RequestFactory().post("/graphql")
        self.request.user = self.admin
        self.context = {"request": self.request}
        self.url = "https://example.com/preview-page"

    def _in_progress_preview(self) -> SourcePreview:
        return SourcePreview.objects.create(
            url=self.url,
            created_by=self.admin,
            status=SourcePreview.PREVIEW_STATUS.IN_PROGRESS,
        )

    @patch("apps.entry.tasks.generate_pdf.delay")
    def test_default_reuses_recent_existing(self, _mock_delay):
        """Default (skip_recent_reuse absent/False) returns the matching IN_PROGRESS preview."""
        existing = self._in_progress_preview()

        serializer = SourcePreviewSerializer(data={"url": self.url}, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        instance = serializer.save()

        self.assertEqual(instance.pk, existing.pk)
        self.assertEqual(SourcePreview.objects.count(), 1)

    @patch("apps.entry.tasks.generate_pdf.delay")
    def test_skip_recent_reuse_creates_new(self, _mock_delay):
        """skip_recent_reuse=True always creates a fresh preview (hulk bulk path)."""
        existing = self._in_progress_preview()

        serializer = SourcePreviewSerializer(
            data={"url": self.url, "skip_recent_reuse": True},
            context=self.context,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        instance = serializer.save()

        self.assertNotEqual(instance.pk, existing.pk)
        self.assertEqual(SourcePreview.objects.count(), 2)

    @patch("apps.entry.tasks.generate_pdf.delay")
    def test_skip_recent_reuse_not_leaked_into_response_data(self, _mock_delay):
        """The write-only flag must not surface in serialized output."""
        serializer = SourcePreviewSerializer(
            data={"url": self.url, "skip_recent_reuse": True},
            context=self.context,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertNotIn("skip_recent_reuse", serializer.data)
