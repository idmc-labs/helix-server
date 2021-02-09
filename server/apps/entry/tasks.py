import dramatiq
import pdfkit
from django.core.files.base import ContentFile


@dramatiq.actor
def generate_pdf(pk):
    from apps.contrib.models import SourcePreview

    source_preview = SourcePreview.objects.get(pk=pk)
    url = source_preview.url
    path = SourcePreview.PREVIEW_FOLDER + '/' + source_preview.token + '.pdf'
    source_preview.status = SourcePreview.PREVIEW_STATUS.IN_PROGRESS
    source_preview.save()
    try:
        pdf_content = pdfkit.from_url(url, False)
        source_preview.pdf.save(path, ContentFile(pdf_content))
        source_preview.status = SourcePreview.PREVIEW_STATUS.COMPLETED
    except Exception:
        source_preview.status = SourcePreview.PREVIEW_STATUS.FAILED
        source_preview.remark = 'Could not generate pdf'

    source_preview.save()
