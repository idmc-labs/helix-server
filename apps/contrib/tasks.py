import logging
import re
from tempfile import NamedTemporaryFile
import time
from datetime import timedelta

from django.core.files import File
from django.conf import settings
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

# from helix.settings import QueuePriority
from helix.celery import app as celery_app


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_excel_sheet_content(headers, data, **kwargs):
    wb = Workbook(write_only=True)

    ws = wb.create_sheet('Main')

    def append_to_worksheet(_ws, _headers, _data, _transformer):
        keys = _headers.keys()
        _ws.append([_headers[key] for key in keys])
        for _datum in _data.iterator(chunk_size=2000):
            transformed_datum = _datum
            if _transformer:
                transformed_datum = _transformer(_datum)
            _ws.append([
                re.sub(ILLEGAL_CHARACTERS_RE, '', str(transformed_datum.get(key)) if transformed_datum.get(key) else '')
                for key in keys
            ])

    # append the primary sheet
    append_to_worksheet(ws, headers, data, kwargs.get('transformer'))
    # append the secondary sheets if provided
    for other in kwargs.get('other', []):
        ws = wb.create_sheet(other['title'])
        headers = other['results']['headers']
        data = other['results']['data']
        transformer = other['results'].get('transformer')
        append_to_worksheet(ws, headers, data, transformer)

    return wb


@celery_app.task(time_limit=settings.EXCEL_EXPORT_PROGRESS_STATE_TIMEOUT)
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
        workbook = get_excel_sheet_content(**sheet_data)
        with NamedTemporaryFile(dir='/tmp') as tmp:
            workbook.save(tmp.name)
            workbook.close()
            download.file.save(path, File(tmp))
            del workbook
        download.status = ExcelDownload.EXCEL_GENERATION_STATUS.COMPLETED
        download.completed_at = timezone.now()
        download.save()

        logger.warn(f'Completed sheet generation for ExcelDownload={download_id} in {time.time() - then}')
    except Exception as e:  # NOQA E722
        logger.error(f'Error: Sheet generation for ExcelDownload={download_id}', exc_info=True)
        download.status = ExcelDownload.EXCEL_GENERATION_STATUS.FAILED
        download.completed_at = timezone.now()
        download.save(update_fields=['status'])


@celery_app.task
def kill_all_old_excel_exports():
    from apps.contrib.models import ExcelDownload

    # if a task has been pending for too long, move it to killed
    pending = ExcelDownload.objects.filter(
        status=ExcelDownload.EXCEL_GENERATION_STATUS.PENDING,
        started_at__lte=timezone.now() - timedelta(seconds=settings.EXCEL_EXPORT_PENDING_STATE_TIMEOUT),
    ).update(status=ExcelDownload.EXCEL_GENERATION_STATUS.KILLED)

    # if a task has been in progress beyond timeout, move it to killed
    progress = ExcelDownload.objects.filter(
        status=ExcelDownload.EXCEL_GENERATION_STATUS.IN_PROGRESS,
        started_at__lte=timezone.now() - timedelta(seconds=settings.EXCEL_EXPORT_PROGRESS_STATE_TIMEOUT),
    ).update(status=ExcelDownload.EXCEL_GENERATION_STATUS.KILLED)

    logger.info(f'Updated excel exports to killed:\n{pending=}\n{progress=}')
