import logging

from django.core.cache import cache
from django.core.management.base import BaseCommand

from apps.extraction.models import QueryAbstractModel

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Drop the cached filter kwargs of every report and extraction query. "
        "Run after a deployment that writes filters outside the save path."
    )

    def handle(self, *args, **kwargs):
        # The key carries `modified_at`, so an edit through the serializer or admin invalidates by
        # itself. A write that bypasses the save -- a data migration or a manual SQL fix -- leaves
        # the stamp untouched, and the entry then serves the pre-write filters for the whole TTL.
        pattern = f"{QueryAbstractModel.FILTER_KWARGS_CACHE_PREFIX}:*"
        deleted = cache.delete_pattern(pattern)
        self.stdout.write(self.style.SUCCESS(f"Cleared {deleted} cached filter-kwargs entries ({pattern})"))
