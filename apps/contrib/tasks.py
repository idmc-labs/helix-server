import logging
import re
from tempfile import NamedTemporaryFile
import time

from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone
import dramatiq
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

from helix.settings import QueuePriority


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_excel_sheet_content(headers, data, **kwargs):
    wb = Workbook(write_only=True)

    ws = wb.create_sheet('Main')

    def append_to_worksheet(_ws, _headers, _data):
        keys = _headers.keys()
        _ws.append([_headers[key] for key in keys])
        for elements in _data:
            _ws.append([
                re.sub(ILLEGAL_CHARACTERS_RE, '', str(elements.get(key)) if elements.get(key) else '')
                for key in keys
            ])
    append_to_worksheet(ws, headers, data)
    for other in kwargs.get('other', []):
        ws = wb.create_sheet(other['title'])
        headers = other['results']['headers']
        data = other['results']['data']
        append_to_worksheet(ws, headers, data)

    with NamedTemporaryFile() as tmp:
        wb.save(tmp.name)
        tmp.seek(0)
        content = tmp.read()
        return content


@dramatiq.actor(
    queue_name=QueuePriority.HEAVY.value,
    max_retries=0,
    time_limit=settings.EXCEL_EXPORT_PROGRESS_STATE_TIMEOUT * 1000
)
def generate_excel_file(download_id, user_id):
    '''
    Fetch the filter data from excel download
    Fetch the request from the task argument
    Call appropriate model excel data getter
    '''
    from apps.contrib.models import ExcelDownload
    download = ExcelDownload.objects.get(id=download_id)
    download.started_at = timezone.now()
    download.status = ExcelDownload.EXCEL_GENERATION_STATUS.IN_PROGRESS
    download.save()
    try:
        then = time.time()
        path = f'{download.download_type.name}-{download.started_at.isoformat()}.xlsx'

        logger.warn(f'Starting sheet generation for ExcelDownload={download_id}...')
        sheet_data_getter = download.get_model_sheet_data_getter()
        sheet_data = sheet_data_getter(user_id=user_id, filters=download.filters)
        content = get_excel_sheet_content(**sheet_data)
        download.file.save(path, ContentFile(content))
        download.status = ExcelDownload.EXCEL_GENERATION_STATUS.COMPLETED
        download.completed_at = timezone.now()
        download.save()

        logger.warn(f'Completed sheet generation for ExcelDownload={download_id} in {time.time() - then}')
    except Exception as e:  # NOQA E722
        logger.error(f'Error: Sheet generation for ExcelDownload={download_id}', exc_info=True)
        download.status = ExcelDownload.EXCEL_GENERATION_STATUS.FAILED
        download.completed_at = timezone.now()
        download.save(update_fields=['status'])
