from django.conf import settings
from django.test import RequestFactory
from django.utils import timezone

from apps.contrib.models import ExcelDownload
from apps.contrib.serializers import ExcelDownloadSerializer
from apps.users.enums import USER_ROLE
from utils.tests import HelixTestCase, create_user_with_role


class TestExcelDownload(HelixTestCase):
    def setUp(self) -> None:
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.request = RequestFactory().post('/graphql')
        self.context = dict()

    def test_valid_excel_export_if_all_complete(self):
        self.request.user = self.admin
        self.context['request'] = self.request
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
                filters=dict(),
            ),
            context=self.context,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_excel_export_if_in_progress_beyond_limit(self):
        self.request.user = self.admin
        self.context['request'] = self.request
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
                filters=dict(),
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
                filters=dict(),
            ),
            context=self.context,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertEqual('limited-at-a-time', serializer.errors['non_field_errors'][0].code)

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
                filters=dict(),
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
                filters=dict(),
            ),
            context=self.context,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
