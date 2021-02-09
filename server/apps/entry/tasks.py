import dramatiq
import pdfkit
from django.core.files.base import ContentFile


@dramatiq.actor
def generate_pdf(pk, url, path):
    from apps.contrib.models import SourcePreview

    source_preview = SourcePreview.objects.get(pk=pk)
    try:
        # config = pdfkit.configuration(wkhtmltopdf='/opt/bin/wkhtmltopdf')
        # pdf_content = pdfkit.from_url(url, False, configuration=config)
        pdf_content = pdfkit.from_url(url, False)
        source_preview.pdf.save(path, ContentFile(pdf_content))
    except Exception:
        source_preview.reason = 'Could not generate pdf'

    source_preview.completed = True
    source_preview.save()
