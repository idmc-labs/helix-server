"""
https://github.com/jcass77/django-apscheduler
"""

from datetime import timedelta
import logging
import signal

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from django.utils import timezone
from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoMemoryJobStore
from django_apscheduler.models import DjangoJobExecution


logger = logging.getLogger(__name__)


def fail_all_old_excel_exports():
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


def delete_old_job_executions(max_age=settings.OLD_JOB_EXECUTION_TTL):
    """This job deletes all apscheduler job executions older than `max_age` seconds from the database."""
    DjangoJobExecution.objects.delete_old_job_executions(max_age)


class Command(BaseCommand):
    help = "Runs apscheduler."

    def handle(self, *args, **options):
        # NOTE: be careful to ensure that you only have one scheduler actively running at a particular point in time.
        # So as a remedy we will create a job on startup, and check it from other services
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)

        scheduler.add_jobstore(DjangoMemoryJobStore(), "default")
        scheduler.add_job(
            delete_old_job_executions,
            trigger=CronTrigger(
                day_of_week="mon", hour="00", minute="00"
            ),  # Midnight on Monday, before start of the next work week.
            id="delete_old_job_executions",
            max_instances=1,
            replace_existing=True,
        )

        scheduler.add_job(
            fail_all_old_excel_exports,
            trigger=CronTrigger(minute="*/10"),
            id="fail_all_old_excel_exports",  # The `id` assigned to each job MUST be unique
            # NOTE: be careful to ensure that you only have one scheduler actively running at a particular point in time.
            max_instances=1,
            replace_existing=True,
        )

        def shutdown(*args):
            logger.info("Stopping scheduler...")
            scheduler.shutdown()

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        out = "\n\nDiscovering jobs...\n"
        for item in scheduler.get_jobs():
            out += f"* {item.name} - {item.trigger}\n"
        logger.info(out)

        logger.info("Starting scheduler...")
        scheduler.start()
