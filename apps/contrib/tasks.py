import logging
import re
from tempfile import NamedTemporaryFile
import time

from django.core.files.base import ContentFile
from django.utils import timezone
import dramatiq
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

from helix.settings import QueuePriority

TIMEOUT = 2 * 60 * 1000  # 2 minutes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_excel_sheet_content(headers, data, **kwargs):
    wb = Workbook(write_only=True)
    ws = wb.create_sheet('Sheet 1')
    keys = headers.keys()
    ws.append([headers[key] for key in keys])
    for elements in data:
        ws.append([re.sub(ILLEGAL_CHARACTERS_RE, '', str(elements.get(key)) if elements.get(key) else '') for key in keys])
    with NamedTemporaryFile() as tmp:
        wb.save(tmp.name)
        tmp.seek(0)
        content = tmp.read()
        return content


@dramatiq.actor(queue_name=QueuePriority.DEFAULT.value, max_retries=1, time_limit=TIMEOUT)
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
        download.save(update_fields=['status'])
