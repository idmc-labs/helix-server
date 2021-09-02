import logging
import re
from tempfile import NamedTemporaryFile
import time
from datetime import timedelta

from django.core.files import File
from django.conf import settings
from django.db import models
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

# from helix.settings import QueuePriority
from helix.celery import app as celery_app
from apps.entry.tasks import PDF_TASK_TIMEOUT
from apps.report.tasks import REPORT_TIMEOUT


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
            file = File(tmp)
            download.file_size = file.size
            download.file.save(path, file)
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
    ).filter(
        models.Q(
            started_at__isnull=False,
            started_at__lte=timezone.now() - timedelta(seconds=settings.EXCEL_EXPORT_PENDING_STATE_TIMEOUT),
        ) | models.Q(
            created_at__lte=timezone.now() - timedelta(seconds=settings.EXCEL_EXPORT_PENDING_STATE_TIMEOUT * 3),
        )
    ).update(status=ExcelDownload.EXCEL_GENERATION_STATUS.KILLED)

    # if a task has been in progress beyond timeout, move it to killed
    progress = ExcelDownload.objects.filter(
        status=ExcelDownload.EXCEL_GENERATION_STATUS.IN_PROGRESS,
        started_at__lte=timezone.now() - timedelta(seconds=settings.EXCEL_EXPORT_PROGRESS_STATE_TIMEOUT),
    ).update(status=ExcelDownload.EXCEL_GENERATION_STATUS.KILLED)

    logger.info(f'Updated EXCEL EXPORTS to killed:\n{pending=}\n{progress=}')


@celery_app.task
def kill_all_long_running_previews():
    from apps.contrib.models import SourcePreview

    progress = SourcePreview.objects.filter(
        status=SourcePreview.PREVIEW_STATUS.IN_PROGRESS,
        created_at__lte=timezone.now() - timedelta(seconds=PDF_TASK_TIMEOUT * 5),
    ).update(status=SourcePreview.PREVIEW_STATUS.KILLED)

    logger.info(f'Updated SOURCE PREVIEWS to killed:\n{progress=}')


@celery_app.task
def kill_all_long_running_report_generations():
    from apps.report.models import ReportGeneration

    progress = ReportGeneration.objects.filter(
        status=ReportGeneration.REPORT_GENERATION_STATUS.IN_PROGRESS,
        created_at__lte=timezone.now() - timedelta(seconds=REPORT_TIMEOUT * 2),
    ).update(status=ReportGeneration.REPORT_GENERATION_STATUS.KILLED)

    logger.info(f'Updated REPORT GENERATION to killed:\n{progress=}')
