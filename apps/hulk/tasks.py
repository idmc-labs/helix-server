from __future__ import annotations

import datetime
import logging

from django.utils import timezone

from apps.hulk.bulk.handler import HulkBulkImportHandler
from helix.celery import app as celery_app

from .models import HulkBulkImport

logger = logging.getLogger(__name__)


@celery_app.task
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
