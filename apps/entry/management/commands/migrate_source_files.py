import csv
import magic
import os
import typing
from django.core.management.base import BaseCommand, CommandParser

from apps.entry.models import Entry
from apps.contrib.models import Attachment, SourcePreview


class Command(BaseCommand):
    """
    Migrate Source files of helix 1.0 to helix 2.0,
    Any PDF created using wkhtmltopdf or one of the browsers should be considered as a URL type entry,
    Everything else should be considered as a Document type entry
    """

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('csv_file_path', type=str, help="Path to the CSV file containing the data.")

    def convert_entry_to_document_type(self, entry: Entry):
        """Create a document attachment and detach the preview from the entry."""
        with entry.preview.pdf.open('rb') as file:
            byte_stream = file.read()
            filetype_detail = magic.Magic().id_buffer(byte_stream)
            encoding = magic.Magic(flags=magic.MAGIC_MIME_ENCODING).id_buffer(byte_stream)

        entry.document = Attachment.objects.create(
            attachment_for=Attachment.FOR_CHOICES.ENTRY,
            attachment=entry.preview.pdf,
            mimetype='application/pdf',
            encoding=encoding,
            filetype_detail=filetype_detail,
        )
        entry.document_url = entry.url
        entry.url = None
        entry.preview = None
        entry.save(
            update_fields=[
                "document",
                "document_url",
                "url",
                "preview",
            ]
        )

    def convert_entry_to_url_type(self, entry: Entry):
        """Create a SourcePreview and detach the document from the entry."""
        entry.preview = SourcePreview.objects.create(
            url=entry.document_url,
            pdf=entry.document.attachment,
            status=SourcePreview.PREVIEW_STATUS.COMPLETED,
        )
        entry.url = entry.document_url
        entry.document_url = None
        entry.document = None
        entry.save(
            update_fields=[
                "preview",
                "url",
                "document",
                "document_url",
            ]
        )

    def handle(self, *args: typing.Any, **kwargs: typing.Any):
        csv_file_path = kwargs['csv_file_path']
        updated_documents_count = 0
        updated_previews_count = 0

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"CSV file path does not exist: {csv_file_path}"))
            return

        # NOTE: Create a mapping of filename to metadata
        mapping: dict[str, dict] = {}
        with open(csv_file_path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                mapping[row['filename']] = row

        # NOTE: We should check if the filepath starts with helix-old/ because it might have changed
        entry_with_previews_from_helix1 = Entry.objects.filter(
            old_id__isnull=False,
            preview__pdf__startswith='helix-old/',
        )
        # NOTE: entry with previews and documents should be zero
        assert entry_with_previews_from_helix1.filter(document__isnull=False).count() == 0

        for entry in entry_with_previews_from_helix1:
            filename = entry.preview.pdf.name.split('helix-old/')[1]
            metadata = mapping.get(filename)
            if (metadata and metadata['type'] == 'document'):
                self.convert_entry_to_document_type(entry=entry)
                self.stdout.write(self.style.SUCCESS(f"Converted entry {entry.id} to document type."))
                updated_documents_count += 1

        # NOTE: We should check if the filepath starts with helix-old/ because it might have changed
        entry_with_documents_from_helix1 = Entry.objects.filter(
            old_id__isnull=False,
            document__attachment__startswith='helix-old/',
        )
        # NOTE: entry with documents and previews should be zero
        assert entry_with_documents_from_helix1.filter(preview__isnull=False).count() == 0

        for entry in entry_with_documents_from_helix1:
            filename = entry.document.attachment.name.split('helix-old/')[1]
            metadata = mapping.get(filename)
            if (metadata and metadata['type'] == 'url' and entry.document_url):
                self.convert_entry_to_url_type(entry=entry)
                self.stdout.write(self.style.SUCCESS(f"Converted entry {entry.id} to url type."))
                updated_previews_count += 1

        self.stdout.write(self.style.SUCCESS(f"Updated {updated_documents_count} entries to document type."))
        self.stdout.write(self.style.SUCCESS(f"Updated {updated_previews_count} entries to url type."))
