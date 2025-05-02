import csv
import os
import typing

import magic
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from apps.contrib.models import Attachment, SourcePreview
from apps.entry.models import Entry
from helix.managers import BulkUpdateManager


class Command(BaseCommand):
    """
    Migrate Source files of helix 1.0 to helix 2.0,
    Any PDF created using wkhtmltopdf or one of the browsers should be considered as a URL type entry,
    Everything else should be considered as a Document type entry
    """

    def __init__(self) -> None:
        super().__init__()
        self.magic_type = magic.Magic()
        self.magic_encoding = magic.Magic(flags=magic.MAGIC_MIME_ENCODING)

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("csv_file_path", type=str, help="Path to the CSV file containing the data.")

    def convert_entry_to_document_type(self, entry: Entry, bulk_mgr: BulkUpdateManager):
        """Create a document attachment and detach the preview from the entry."""
        with entry.preview.pdf.open("rb") as file:
            byte_stream = file.read(2048)
            filetype_detail = self.magic_type.id_buffer(byte_stream)
            encoding = self.magic_encoding.id_buffer(byte_stream)

        entry.document = Attachment.objects.create(
            attachment_for=Attachment.FOR_CHOICES.ENTRY,
            attachment=entry.preview.pdf,
            mimetype="application/pdf",
            encoding=encoding,
            filetype_detail=filetype_detail,
        )
        entry.document_url = entry.url
        entry.url = None
        entry.preview = None
        bulk_mgr.add(entry)

    def convert_entry_to_url_type(self, entry: Entry, bulk_mgr: BulkUpdateManager):
        """Create a SourcePreview and detach the document from the entry."""
        entry.preview = SourcePreview.objects.create(
            url=entry.document_url,
            pdf=entry.document.attachment,
            status=SourcePreview.PREVIEW_STATUS.COMPLETED,
        )
        entry.url = entry.document_url
        entry.document_url = None
        entry.document = None
        bulk_mgr.add(entry)

    @transaction.atomic
    def handle(self, *args: typing.Any, **kwargs: typing.Any):
        updated_documents_count = 0
        updated_previews_count = 0

        csv_file_path = kwargs["csv_file_path"]
        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"CSV file path does not exist: {csv_file_path}"))
            return

        # NOTE: Create a mapping of filename to metadata
        mapping: dict[str, dict] = {}
        with open(csv_file_path, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                mapping[row["filename"]] = row

        # NOTE: We should check if the filepath starts with helix-old/ because it might have changed
        entry_with_previews_from_helix1 = Entry.objects.filter(
            old_id__isnull=False,
            preview__pdf__startswith="helix-old/",
        )
        # NOTE: entry with previews and documents should be zero
        assert entry_with_previews_from_helix1.filter(document__isnull=False).count() == 0

        bulk_mgr = BulkUpdateManager(["document", "document_url", "url", "preview"], chunk_size=1000)
        for entry in entry_with_previews_from_helix1.iterator():
            filename = entry.preview.pdf.name.split("helix-old/")[1]
            metadata = mapping.get(filename)
            if not metadata:
                self.stdout.write(self.style.ERROR(f"Metadata not found for Entry ({entry.id}) with filename ({filename})"))
                continue
            if metadata["type"] == "document":
                self.convert_entry_to_document_type(entry=entry, bulk_mgr=bulk_mgr)
                self.stdout.write(self.style.SUCCESS(f"Converting entry {entry.id} to document type."))
                updated_documents_count += 1

        # NOTE: We should check if the filepath starts with helix-old/ because it might have changed
        entry_with_documents_from_helix1 = Entry.objects.filter(
            old_id__isnull=False,
            document__attachment__startswith="helix-old/",
        )
        # NOTE: entry with documents and previews should be zero
        assert entry_with_documents_from_helix1.filter(preview__isnull=False).count() == 0

        for entry in entry_with_documents_from_helix1.iterator():
            filename = entry.document.attachment.name.split("helix-old/")[1]
            metadata = mapping.get(filename)
            if not metadata:
                self.stdout.write(self.style.ERROR(f"Metadata not found for Entry ({entry.id}) with filename ({filename})"))
                continue
            if metadata["type"] == "url" and entry.document_url:
                self.convert_entry_to_url_type(entry=entry, bulk_mgr=bulk_mgr)
                self.stdout.write(self.style.SUCCESS(f"Converting entry {entry.id} to url type."))
                updated_previews_count += 1

        bulk_mgr.done()
        self.stdout.write(self.style.SUCCESS(f"Successfully updated {bulk_mgr.summary()} entries."))
        self.stdout.write(self.style.SUCCESS(f"Updated {updated_documents_count} entries to document type."))
        self.stdout.write(self.style.SUCCESS(f"Updated {updated_previews_count} entries to url type."))
