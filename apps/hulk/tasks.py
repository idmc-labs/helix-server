from __future__ import annotations

import datetime
import logging

from django.utils import timezone

from apps.hulk.bulk.handler import HulkBulkImportHandler
from helix.celery import app as celery_app

from .models import HulkBulkImport

logger = logging.getLogger(__name__)

# Max wall-clock time a single bulk import may run. Used in two places that
# MUST stay consistent:
#   1. The Celery time limit on ``process_hulk_bulk_import`` — a live worker
#      aborts (and the handler marks the row FAILED) once an import overruns.
#   2. The staleness threshold used by ``fail_stale_hulk_bulk_imports`` —
#      the backstop that frees the global single-import lock when the worker
#      itself died (deploy restart, OOM, kill) and so never hit its own limit.
HULK_IMPORT_PROGRESS_TIMEOUT = 2 * 60 * 60  # seconds (2 hours)
# Small grace between the soft limit (raises SoftTimeLimitExceeded inside the
# task so the handler can fail the row cleanly) and the hard limit (force kill).
HULK_IMPORT_HARD_TIMEOUT_GRACE = 60  # seconds


@celery_app.task(
    soft_time_limit=HULK_IMPORT_PROGRESS_TIMEOUT,
    time_limit=HULK_IMPORT_PROGRESS_TIMEOUT + HULK_IMPORT_HARD_TIMEOUT_GRACE,
)
def process_hulk_bulk_import(bulk_import_id: int):
    logger.info("Running process_hulk_bulk_import: %s", bulk_import_id)

    bulk_import = HulkBulkImport.objects.get(pk=bulk_import_id)
    # If the row sat in PENDING longer than the threshold (worker outage,
    # backed-up queue), skip it rather than running a possibly stale import.
    # Already-progressed rows are left to the handler's own CAS guard.
    if bulk_import.status == HulkBulkImport.HULK_BULK_IMPORT_STATUS.PENDING and (
        timezone.now() - bulk_import.created_at > datetime.timedelta(minutes=HulkBulkImport.WAIT_TIME_THRESHOLD_IN_MINUTES)
    ):
        logger.warning("Skipping stale hulk bulk import: %s", bulk_import_id)
        bulk_import.update_status(HulkBulkImport.HULK_BULK_IMPORT_STATUS.SKIPPED)
        return

    handler = HulkBulkImportHandler(bulk_import)
    handler.handle()


@celery_app.task
def fail_stale_hulk_bulk_imports():
    """Free the global single-import lock from imports orphaned by a dead worker.

    An import stuck at IN_PROGRESS (its worker was restarted/OOM-killed before
    finishing, so the task's own time limit never fired) otherwise blocks every
    new import indefinitely, since only one import may be active at a time.
    Anything that has been IN_PROGRESS past the max run time cannot still be
    running legitimately, so mark it FAILED. PENDING rows are handled separately
    by ``process_hulk_bulk_import`` (the WAIT_TIME_THRESHOLD stale-skip).
    """
    stale = HulkBulkImport.objects.filter(
        status=HulkBulkImport.HULK_BULK_IMPORT_STATUS.IN_PROGRESS,
        started_at__lte=timezone.now() - datetime.timedelta(seconds=HULK_IMPORT_PROGRESS_TIMEOUT),
    ).update(
        status=HulkBulkImport.HULK_BULK_IMPORT_STATUS.FAILED,
        completed_at=timezone.now(),
    )
    logger.info("Marked stale IN_PROGRESS hulk bulk imports as FAILED: %s", stale)
    return stale
