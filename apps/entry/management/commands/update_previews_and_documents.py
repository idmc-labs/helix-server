import csv
import uuid
from urllib.request import urlretrieve
from django.core.management.base import BaseCommand
from django.core.files import File
from apps.entry.models import Entry
from apps.contrib.models import Attachment, SourcePreview
from apps.contrib.serializers import AttachmentSerializer


class Command(BaseCommand):

    help = "Update preview of entries"

    def add_arguments(self, parser):
        parser.add_argument('source_preview_csv_file')
        parser.add_argument('document_attachment_csv_file')

    def handle(self, *args, **kwargs):
        source_preview_csv_file = kwargs['source_preview_csv_file']
        with open(source_preview_csv_file, 'r') as source_preview_csv_file:
            reader = csv.DictReader(source_preview_csv_file)

            entry_old_id_and_filename_map = {obj['id']: obj['filename'] for obj in reader}

            source_preview_csv_file.seek(0)
            next(reader)

            entry_old_id_and_url_map = {obj['id']: obj['url'] for obj in reader}

            # Get entries having preview url None
            # TODO: Should we update all the entry objects?
            entries = Entry.objects.filter(
                old_id__in=entry_old_id_and_url_map.keys(),
                preview__url__isnull=True,
            )

            # Only create preview if preview url is None, or preview is None
            for entry in entries:
                url = entry_old_id_and_url_map[entry.old_id]
                pdf = entry_old_id_and_filename_map[entry.old_id]

                if not entry.preview:
                    source_preview = SourcePreview.objects.create(
                        url=url,
                        pdf=pdf,
                        status=SourcePreview.PREVIEW_STATUS.COMPLETED,
                        token=str(uuid.uuid4()),
                    )
                    entry.preview = source_preview
                    print(
                        "Preview created for \n",
                        f"entry_id      => {entry.id}\n",
                        f"entry old_id  => {entry.old_id}\n",
                        f"Preview url   => {entry.preview.url}\n",
                        f"Preview pdf   => {entry.preview.pdf.url}\n",
                        "\n\n"
                    )

                    if entry.document:
                        # TODO: Should we remove document as well?
                        # TODO: Should we delete attachment object too?
                        entry.document.attachment = None
                        entry.document.attachment_for = None
                        entry.document.mimetype = None
                        entry.document.encoding = None
                        entry.document.filetype_detail = None
                    entry.save()

        document_attachment_csv_file = kwargs['document_attachment_csv_file']
        with open(document_attachment_csv_file, 'r') as document_attachment_csv_file:
            reader = csv.DictReader(document_attachment_csv_file)
            entry_old_id_and_attachment_map = {obj['id']: obj['filename'] for obj in reader}

            # Get entries having document url None
            # TODO: Should we update all the entry objects?, some of entries document may be updated,
            # in this case we should not update all of them
            entries = Entry.objects.filter(
                old_id__in=entry_old_id_and_attachment_map.keys(),
                document__attachment__isnull=True,
            )
            for entry in entries:
                if not entry.document:
                    filename = entry_old_id_and_attachment_map[entry.old_id]
                    url = f"https://helix-copilot-staging-helix-media.s3.amazonaws.com/media/helix-old/{filename}"
                    file_content, _ = urlretrieve(url)
                    attachment = AttachmentSerializer(data={
                        "attachment": File(open(file_content, 'rb'), name=filename),
                        "attachment_for": Attachment.FOR_CHOICES.ENTRY.value,
                    })
                    if attachment.is_valid():
                        attachment = attachment.save()
                        entry.document = attachment
                        if entry.preview:
                            # TODO: Should we remove preview urls and pdf as well?
                            # TODO: Should we delete attachment object too?
                            entry.preview.url = None
                            entry.preview.token = None
                            entry.preview.pdf = None
                            # What should be value of status?
                            entry.preview.status = SourcePreview.PREVIEW_STATUS.FAILED.value
                            entry.preview.remark = None
                            entry.save()
                            print(
                                "Document created for \n",
                                f"entry_id       => {entry.id}\n",
                                f"entry old_id   => {entry.old_id}\n",
                                f"Attachment url => {entry.document.attachment.url}\n",
                                "\n\n"
                            )
                    else:
                        print(
                            attachment.errors, '\n'
                            f"entry_id       => {entry.id}\n",
                            f"entry old_id   => {entry.old_id}\n",
                            "\n\n"
                        )
