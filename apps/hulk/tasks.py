from __future__ import annotations

import logging

from apps.hulk.bulk.handler import HulkBulkImportHandler
from helix.celery import app as celery_app

from .models import HulkBulkImport

logger = logging.getLogger(__name__)


@celery_app.task
def process_hulk_bulk_import(bulk_import_id: int):
    logger.info("Running process_hulk_bulk_import: %s", bulk_import_id)

    bulk_import = HulkBulkImport.objects.get(pk=bulk_import_id)
    handler = HulkBulkImportHandler(bulk_import)
    handler.handle()
