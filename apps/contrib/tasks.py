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
from apps.entry.tasks import PDF_TASK_TIMEOUT
from apps.report.tasks import REPORT_TIMEOUT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_excel_sheet_content(headers, data, **kwargs):
    wb = Workbook(write_only=True)

    ws = wb.create_sheet('Main')

    def clean_data_item(item):
        # NOTE: we are using isinstance(item, int) because 0 is falsy value
        if isinstance(item, int):
            return item
        elif isinstance(item, str):
            return re.sub(ILLEGAL_CHARACTERS_RE, '', item)
        elif item:
            return str(item)
        return ''

    def append_to_worksheet(_ws, _headers, _data, _transformer):
        keys = _headers.keys()
        _ws.append([_headers[key] for key in keys])
        for _datum in _data.iterator(chunk_size=2000):
            transformed_datum = _datum
            if _transformer:
                transformed_datum = _transformer(_datum)
            _ws.append([
                clean_data_item(transformed_datum.get(key))
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


def save_download_file(download, workbook, path):
    with NamedTemporaryFile(dir='/tmp') as tmp:
        workbook.save(tmp.name)
        workbook.close()
        file = File(tmp)
        download.file_size = file.size
        download.file.save(path, file)
        del workbook


@celery_app.task(time_limit=settings.EXCEL_EXPORT_PROGRESS_STATE_TIMEOUT)
def generate_excel_file(download_id, user_id, model_instance_id=None):
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
        if (
            ExcelDownload.DOWNLOAD_TYPES.INDIVIDUAL_REPORT == download.download_type and
            model_instance_id is not None
        ):
            from apps.report.models import Report
            from apps.report.utils import report_get_excel_sheets_data
            from apps.report.tasks import generate_excel_file as report_generate_excel_file
            report = Report.objects.get(id=model_instance_id)
            excel_sheet_data = report_get_excel_sheets_data(report).items()
            workbook = report_generate_excel_file(excel_sheet_data)
            save_download_file(download, workbook, path)
        else:
            sheet_data_getter = download.get_model_sheet_data_getter()
            sheet_data = sheet_data_getter(user_id=user_id, filters=download.filters)
            workbook = get_excel_sheet_content(**sheet_data)
            save_download_file(download, workbook, path)
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
        created_at__lte=timezone.now() - timedelta(seconds=settings.EXCEL_EXPORT_PENDING_STATE_TIMEOUT),
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


@celery_app.task
def generate_idus_dump_file():
    import json
    from apps.entry.models import ExternalApiDump
    from apps.entry.serializers import FigureReadOnlySerializer
    from apps.entry.views import get_idu_data
    from utils.common import get_temp_file

    external_api_dump, created = ExternalApiDump.objects.get_or_create(
        api_type=ExternalApiDump.ExternalApiType.IDUS.value,
    )
    try:
        serializer = FigureReadOnlySerializer(get_idu_data(), many=True)
        with get_temp_file(mode="w+") as tmp:
            json.dump(serializer.data, tmp)
            external_api_dump.dump_file.save('idus_dump.json', File(tmp))
        external_api_dump.status = ExternalApiDump.Status.COMPLETED.value
        logger.info('Idus file dump created')
    except Exception:
        external_api_dump.status = ExternalApiDump.Status.FAILED.value
        logger.info('Idus file dump generation failed')
    external_api_dump.save()
