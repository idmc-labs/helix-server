import csv
import random
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.entry.models import Entry
from apps.contrib.models import Attachment
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
            help='Delete documents that are not attached to any entries',
        )

    @transaction.atomic
    def handle(self, *args, **kwargs):
        file_path = kwargs['csv_file_path']
        delete_unused = kwargs.get('delete_unused', False)

        bulk_mgr = BulkUpdateManager(['document_id'])
        document_ids = set()
        used_document_ids = set()
        first_entry_document = list()

        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                entry_id = int(row["entry_id"])
                current_document_id = int(row["document_id"])
                document_ids_list = list(map(int, row["document_ids"].split(", ")))
                document_ids.update(document_ids_list)

                # Set the same document ID for the first entry
                if current_document_id not in used_document_ids:
                    first_entry_document.append(current_document_id)
                    used_document_ids.add(current_document_id)
                    continue

                available_document_ids = [doc_id for doc_id in document_ids_list if doc_id not in used_document_ids]
                if not available_document_ids:
                    self.stdout.write(
                        self.style.WARNING(
                            f"No available document IDs for entry {entry_id}"
                        )
                    )
                    continue

                new_document_id = random.choice(available_document_ids)
                used_document_ids.add(new_document_id)
                bulk_mgr.add(Entry(id=entry_id, document_id=new_document_id))

        bulk_mgr.done()
        self.stdout.write(self.style.SUCCESS(f'Updated document IDs for entries: {bulk_mgr.summary()}'))

        if delete_unused:
            unused_document_ids = document_ids - used_document_ids
            # NOTE: Assert if any used document IDs are in the unused document IDs
            assert not any(doc_id in unused_document_ids for doc_id in used_document_ids)
            if not unused_document_ids:
                self.stdout.write(self.style.WARNING("No unused document IDs found"))
                return
            self.stdout.write(self.style.SUCCESS(f"Deleting unused document IDs: {len(unused_document_ids)}"))
            Attachment.objects.filter(id__in=unused_document_ids).delete()
        raise Exception("This is a test exception")
