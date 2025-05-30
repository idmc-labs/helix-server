import csv

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.entry.models import Entry
from helix.managers import BulkUpdateManager


class Command(BaseCommand):
    help = "Update document IDs for duplicate files"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file_path",
            type=str,
            help="Path to the Document CSV file",
        )

    @transaction.atomic
    def handle(self, *args, **kwargs):
        file_path = kwargs["csv_file_path"]
        bulk_mgr = BulkUpdateManager(["document_id"])

        used_document_ids = set()

        with open(file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                entry_id = int(row["entry_id"])
                # Check if the entry exists
                if not Entry.objects.filter(id=entry_id).first():
                    self.stdout.write(self.style.ERROR(f"Entry ({entry_id}) does not exist"))
                    continue

                current_document_id = int(row["document_id"])
                document_ids_list = list(map(int, row["document_ids"].split(", ")))

                matching_document_ids = sorted([doc_id for doc_id in document_ids_list if doc_id not in used_document_ids])

                if not matching_document_ids:
                    self.stdout.write(self.style.ERROR(f"No documents remaining for Entry ({entry_id})"))
                    continue

                # FIXME: If I am in this list, skip
                new_document_id = matching_document_ids[0]
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Document of Entry ({entry_id}) was updated from ({current_document_id}) to ({new_document_id})"
                    )
                )
                bulk_mgr.add(Entry(id=entry_id, document_id=new_document_id))
                used_document_ids.add(new_document_id)

        bulk_mgr.done()
        self.stdout.write(self.style.SUCCESS(f"Updated document IDs for entries: {bulk_mgr.summary()}"))
