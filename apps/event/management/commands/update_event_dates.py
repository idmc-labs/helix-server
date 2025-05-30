import csv
import logging
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.event.models import Event
from helix.managers import BulkUpdateManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Update event dates"

    def add_arguments(self, parser):
        parser.add_argument("csv_file_path", type=str, help="Path to the CSV file")

    @transaction.atomic
    def handle(self, *args, **kwargs):
        bulk_mgr = BulkUpdateManager(["start_date", "end_date"])

        csv_file_path = kwargs["csv_file_path"]
        with open(csv_file_path, "r") as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                event = Event.objects.filter(old_id=row["old_id"]).first()

                if not event:
                    logger.warning(f"Skipped: Event ({row['old_id']}) not found.")
                    continue

                update_needed = False

                # Update start date
                if row["start_date"]:
                    correct_start_date = datetime.strptime(row["start_date"], "%Y-%m-%d").date()
                    if event.start_date == correct_start_date:
                        # NOTE: No need to migrate the start_date
                        pass
                    elif abs(event.start_date - correct_start_date) == timedelta(days=1):
                        event.start_date = correct_start_date
                        update_needed = True
                    else:
                        logger.warning(
                            f"Flag: For event ({row['old_id']}),"
                            f"delta between actual start_date ({event.start_date}) and"
                            f" the correct start_date ({row['start_date']}) is greater than 1"
                        )

                # Update end date
                if row["end_date"]:
                    correct_end_date = datetime.strptime(row["end_date"], "%Y-%m-%d").date()
                    if event.end_date == correct_end_date:
                        # NOTE: No need to migrate the end_date
                        pass
                    elif abs(event.end_date - correct_end_date) == timedelta(days=1):
                        event.end_date = correct_end_date
                        update_needed = True
                    else:
                        logger.warning(
                            f"Flag: For event ({row['old_id']}),"
                            f"delta between actual end_date ({event.end_date}) and"
                            f" the correct end_date ({row['end_date']}) is greater than 1"
                        )

                if update_needed:
                    bulk_mgr.add(event)

        bulk_mgr.done()
        logger.info(f"Bulk update summary: {bulk_mgr.summary()}")
