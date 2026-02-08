import logging
import time
from types import SimpleNamespace

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db.models import DurationField, ExpressionWrapper, F
from django.utils import timezone
from graphql.execution import ExecutionResult
from tqdm import tqdm

from apps.contrib.models import ExcelDownload
from apps.users.roles import USER_ROLE
from apps.users.utils import HelixInternalBot
from helix.schema import schema
from utils.common import RuntimeProfile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    storage_folder = "profile-benchmark"
    bot = HelixInternalBot()
    context = SimpleNamespace(
        user=bot.user,
        request=SimpleNamespace(user=bot.user),
    )
    export_endpoints = [
        "exportReports",
        "exportUsers",
        "exportParkedItem",
        "exportOrganizations",
        "exportMonitoringSubRegions",
        "exportFigures",
        "exportFigureTags",
        "exportEvents",
        "exportEntries",
        "exportCrises",
        "exportCountries",
        "exportContextOfViolences",
        "exportContacts",
        "exportClients",
        "exportActors",
    ]
    export_timeout_seconds = 60 * 60

    def format_timedelta(self, time_difference: timezone.timedelta) -> str:
        total_seconds = int(time_difference.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        microseconds = time_difference.microseconds

        return f"{hours}:{minutes:02}:{seconds:02}.{microseconds:06}"
    def cleanup_profile_storage_folder(self):
        def delete_recursive(path):
            try:
                directories, files = default_storage.listdir(path)
            except Exception as e:
                logger.exception("Exceptation", e)
                return

            for filename in files:
                file_path = f"{path}/{filename}"
                logger.info(f"Deleting file: {file_path}")
                default_storage.delete(file_path)

            for dirname in directories:
                delete_recursive(f"{path}/{dirname}")

        delete_recursive(self.storage_folder)

    def parse_response_and_get_export_counts(self, response: ExecutionResult):
        result_data = response.data or {}
        result_errors = response.errors or []

        success = []
        failed = []

        for export_name, payload in result_data.items():
            if payload and payload.get("ok") is True:
                success.append(export_name)
            else:
                failed.append(export_name)

        logger.info(
            "Export mutation result | success=%d failed=%d",
            len(success),
            len(failed),
        )

        if success:
            logger.info("Successful exports: %s", ", ".join(success))

        if failed:
            logger.warning("Failed exports: %s", ", ".join(failed))

        if result_errors:
            logger.error("GraphQL errors:")
            for err in result_errors:
                logger.error("  - %s", err)
        return len(success), len(failed)

    def handle_progress(self, datetime_now: timezone.datetime, total_export_count: int, failed_export_count: int):
        counted_ids = set()
        start_time = time.time()

        with tqdm(total=total_export_count + failed_export_count, desc="Generating exports") as pbar:
            pbar.update(failed_export_count)
            while True:
                completed_ids = set(
                    ExcelDownload.objects.filter(
                        status=2,
                        completed_at__isnull=False,
                        completed_at__gte=datetime_now,
                    ).values_list("id", flat=True)
                )

                new_ids = completed_ids - counted_ids
                if new_ids:
                    pbar.update(len(new_ids))
                    counted_ids.update(new_ids)

                pending_count = ExcelDownload.objects.filter(status__in=[0, 1]).count()

                pbar.set_postfix(completed=len(counted_ids), pending=pending_count, failed=failed_export_count)

                if pending_count == 0:
                    break

                if time.time() - start_time > self.export_timeout_seconds:
                    logger.warning("Export polling timed out")
                    break

                time.sleep(0.5)

    def show_export_time_profile(self, datetime_now: timezone.datetime):
        qs = ExcelDownload.objects.filter(
            status=2,
            completed_at__gte=datetime_now,
        )

        downloads = (
            qs.annotate(
                download_time=ExpressionWrapper(
                    F("completed_at") - F("started_at"),
                    output_field=DurationField(),
                )
            )
            .order_by("download_time")
            .values("download_type", "download_time")
        )

        formatted_downloads = [
            {d["download_type"].name.replace("_", " ").title(): self.format_timedelta(d["download_time"])} for d in downloads
        ]

        logger.info(formatted_downloads)

    def handle(self, *args, **options):
        assert getattr(settings, "DEBUG") is True, "This command should run in DEBUG=True mode."

        def generate_mutation(items):
            return "mutation MyMutation {" + "".join(f"{item}(filters: {{}}) {{ ok }}" for item in items) + "}"

        mutation_query = generate_mutation(self.export_endpoints)

        pending_exports = ExcelDownload.objects.filter(status__in=[0, 1]).count()
        logger.info(f"Pending exports before start: {pending_exports}")

        # wait the pending export to complete
        assert pending_exports == 0

        datetime_now = timezone.now()

        logger.info("Cleaning the storage used by profiler")
        self.cleanup_profile_storage_folder()

        logger.info("Starting export")
        with RuntimeProfile("profile export"):
            with self.bot.temporary_role(USER_ROLE.ADMIN):
                response = schema.execute(
                    mutation_query,
                    context_value=self.context,
                )
                total_exports, failed_exports = self.parse_response_and_get_export_counts(response)
            self.handle_progress(datetime_now, total_exports, failed_exports)

        self.show_export_time_profile(datetime_now)
