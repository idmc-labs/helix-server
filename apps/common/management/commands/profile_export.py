import json
import logging
import time
import typing
from types import SimpleNamespace

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db.models import DurationField, ExpressionWrapper, F
from django.utils import timezone
from graphql.execution import ExecutionResult
from tabulate import tabulate
from tqdm import tqdm

from apps.contrib.models import ExcelDownload
from apps.users.roles import USER_ROLE
from apps.users.utils import HelixInternalBot
from helix.schema import schema

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
        return f"{time_difference.total_seconds():.3f}"

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
                        status=ExcelDownload.EXCEL_GENERATION_STATUS.COMPLETED,
                        completed_at__isnull=False,
                        completed_at__gte=datetime_now,
                    ).values_list("id", flat=True)
                )

                new_ids = completed_ids - counted_ids
                if new_ids:
                    pbar.update(len(new_ids))
                    counted_ids.update(new_ids)

                pending_count = ExcelDownload.objects.filter(
                    status__in=[
                        ExcelDownload.EXCEL_GENERATION_STATUS.IN_PROGRESS,
                        ExcelDownload.EXCEL_GENERATION_STATUS.PENDING,
                    ]
                ).count()

                pbar.set_postfix(completed=len(counted_ids), pending=pending_count, failed=failed_export_count)

                if pending_count == 0:
                    break

                if time.time() - start_time > self.export_timeout_seconds:
                    logger.warning("Export polling timed out")
                    break

                time.sleep(0.5)

    def get_export_time_profiles(self, datetime_now: timezone.datetime) -> typing.Dict[str, str]:
        qs = ExcelDownload.objects.filter(
            status=ExcelDownload.EXCEL_GENERATION_STATUS.COMPLETED,
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

        return {
            download["download_type"].name.lower(): self.format_timedelta(download["download_time"])
            for download in downloads
        }

    def show_query_explanation_time_profile(self, export_profile: typing.Dict[str, str]):
        _, files = default_storage.listdir(self.storage_folder)

        benchmarks = []

        for name in files:
            if not name.endswith(".json"):
                continue

            path = f"{self.storage_folder}/{name}"

            with default_storage.open(path, "rb") as f:
                payload = json.loads(f.read())

            benchmarks.append(
                [
                    # BUG: the file extension can be of any length
                    name[:-5],
                    payload["context"]["execution_time_ms"],
                    payload["context"]["planning_time_ms"],
                    # BUG: query explanation time and excel generation can't always be directly linked
                    export_profile.get(name[:-5]),
                ]
            )
        headers = ["Module", "Planning Time(MS)", "Execution Time(MS)", "Excel Generation Time(S)"]
        print(tabulate(benchmarks, headers=headers, tablefmt="github"))

    def handle(self, *args, **options):
        def generate_mutation(items):
            return "mutation MyMutation {" + "".join(f"{item}(filters: {{}}) {{ ok }}" for item in items) + "}"

        mutation_query = generate_mutation(self.export_endpoints)

        pending_exports = ExcelDownload.objects.filter(
            status__in=[ExcelDownload.EXCEL_GENERATION_STATUS.PENDING, ExcelDownload.EXCEL_GENERATION_STATUS.IN_PROGRESS]
        ).count()
        logger.info(f"Pending exports before start: {pending_exports}")

        # wait the pending export to complete
        assert pending_exports == 0

        datetime_now = timezone.now()

        logger.info("Cleaning the storage used by profiler")
        self.cleanup_profile_storage_folder()

        logger.info("Starting export")
        with self.bot.temporary_role(USER_ROLE.ADMIN):
            response = schema.execute(
                mutation_query,
                context_value=self.context,
            )
            total_exports, failed_exports = self.parse_response_and_get_export_counts(response)
        self.handle_progress(datetime_now, total_exports, failed_exports)

        export_profile = self.get_export_time_profiles(datetime_now)

        logger.info("Showing query explanation time profile")
        self.show_query_explanation_time_profile(export_profile)
