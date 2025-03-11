import csv
import random
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.entry.models import Entry
from apps.contrib.models import SourcePreview
from helix.managers import BulkUpdateManager


class Command(BaseCommand):
    help = "Update document IDs for duplicate attachments"

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file_path',
            type=str,
            help='Path to the Document CSV file',
        )
        parser.add_argument(
            '--delete-unused',
            action='store_true',
            help='Delete source preview that are not attached to any entries',
        )

    @transaction.atomic
    def handle(self, *args, **kwargs):
        file_path = kwargs['csv_file_path']
        delete_unused = kwargs.get('delete_unused', False)

        bulk_mgr = BulkUpdateManager(['preview_id'])
        source_preview_ids = set()
        used_source_preview_ids = set()
        first_entry_document = list()

        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                entry_id = int(row["entry_id"])
                url = row["url"]
                current_preview_id = int(row["preview_id"])
                preview_data = row["preview_data"]
