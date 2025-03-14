import csv
import json

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.entry.models import Entry
from helix.managers import BulkUpdateManager


class Command(BaseCommand):
    help = "Update source preview IDs for duplicate pdf files"

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file_path',
            type=str,
            help='Path to the Document CSV file',
        )

    @transaction.atomic
    def handle(self, *args, **kwargs):
        file_path = kwargs['csv_file_path']
        bulk_mgr = BulkUpdateManager(['preview_id'])
        used_source_preview_ids = set()

        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                entry_id = int(row["entry_id"])
                url = row["url"]
                current_preview_id = int(row["preview_id"])

                # Check if the entry exists
                if not Entry.objects.filter(id=entry_id).first():
                    self.stdout.write(
                        self.style.ERROR(f"Entry ID {entry_id} does not exist")
                    )
                    continue

                try:
                    preview_data = json.loads(row["preview_data"])
                except json.JSONDecodeError:
                    self.stdout.write(
                        self.style.ERROR(f"Invalid JSON in preview_data for entry_id {entry_id}")
                    )
                    continue

                # Previews that match the URL
                matching_previews = [
                    preview
                    for preview in preview_data
                    if preview['url'] == url
                ]

                if not matching_previews:
                    self.stdout.write(self.style.ERROR(f"No matched preview for entry {entry_id}"))
                    continue

                # Sorting with id
                matching_previews = sorted(matching_previews, key=lambda x: x['id'])

                available_preview_ids = [
                    preview['id']
                    for preview in matching_previews
                    if preview['id'] not in used_source_preview_ids
                ]

                if not available_preview_ids:
                    self.stdout.write(
                        self.style.ERROR(
                            f"No available preview IDs for entry {entry_id}"
                        )
                    )
                    continue

                new_preview_id = available_preview_ids[0]
                used_source_preview_ids.add(new_preview_id)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Updating EntryID {entry_id}: previewID: ({current_preview_id}) -> ({new_preview_id})"
                    )
                )
                bulk_mgr.add(Entry(id=entry_id, preview_id=new_preview_id))

        bulk_mgr.done()
        self.stdout.write(self.style.SUCCESS(f'Updated preview IDs for entries: {bulk_mgr.summary()}'))
