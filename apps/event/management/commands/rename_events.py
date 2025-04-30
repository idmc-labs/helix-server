import csv
import logging
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.event.models import Event
from helix.managers import BulkUpdateManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Update event names"

    def add_arguments(self, parser):
        parser.add_argument("csv_file_path", type=str, help="Path to the CSV file containing the data.")

    def update_event_names(self, file_path):
        """
        Processes the CSV file and updates the database.
        """
        bulk_mgr = BulkUpdateManager(["name"], chunk_size=1000)

        with open(file_path, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                bulk_mgr.add(
                    Event(
                        id=row["id"],
                        name=row["new_name"],
                    ),
                )

        bulk_mgr.done()
        self.stdout.write(self.style.SUCCESS(f"Bulk update summary: {bulk_mgr.summary()}"))

    @transaction.atomic()
    def handle(self, *args, **kwargs):
        """
        Entry point for processing the CSV file to rename events.
        """
        csv_file_path = kwargs["csv_file_path"]
        if not os.path.exists(csv_file_path):
            logger.error(f"CSV file path does not exist: {csv_file_path}")
            return
        try:
            self.update_event_names(csv_file_path)
            logger.info("Events renamed successfully.")
        except FileNotFoundError:
            logger.error(f"CSV file at {csv_file_path} not found.")
        except Exception:
            logger.error("Failed to rename events:", exc_info=True)
