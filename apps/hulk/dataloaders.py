from collections import defaultdict

from django.db.models import Sum
from promise import Promise
from promise.dataloader import DataLoader

from .models import (
    HulkAttachment,
    HulkBulkImportDataset,
    HulkEntry,
    HulkEvent,
    HulkFigure,
    HulkSourcePreview,
)


class HulkBulkImportSuccessCountLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = (
            HulkBulkImportDataset.objects.filter(bulk_import_id__in=keys)
            .values("bulk_import_id")
            .annotate(total=Sum("success_count"))
        )
        _map = {row["bulk_import_id"]: row["total"] or 0 for row in qs}
        return Promise.resolve([_map.get(key, 0) for key in keys])


class HulkBulkImportFailureCountLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = (
            HulkBulkImportDataset.objects.filter(bulk_import_id__in=keys)
            .values("bulk_import_id")
            .annotate(total=Sum("failure_count"))
        )
        _map = {row["bulk_import_id"]: row["total"] or 0 for row in qs}
        return Promise.resolve([_map.get(key, 0) for key in keys])


class HulkBulkImportSkipCountLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = (
            HulkBulkImportDataset.objects.filter(bulk_import_id__in=keys)
            .values("bulk_import_id")
            .annotate(total=Sum("skip_count"))
        )
        _map = {row["bulk_import_id"]: row["total"] or 0 for row in qs}
        return Promise.resolve([_map.get(key, 0) for key in keys])


class HulkBulkImportDatasetsLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = HulkBulkImportDataset.objects.filter(bulk_import_id__in=keys).order_by("import_type")
        _map = defaultdict(list)
        for dataset in qs:
            _map[dataset.bulk_import_id].append(dataset)
        return Promise.resolve([_map.get(key, []) for key in keys])


class HulkRelationLoaderBase(DataLoader):
    """Load the hulk relation row for an entity, or ``None``.

    An entity was created via the pyhelix (hulk/bulk) interface iff a hulk
    relation row points at it (one-to-one), so we batch-load those rows keyed by
    ``entity_id`` and hand each entity its row (or ``None``).
    """

    hulk_relation_cls = None

    def batch_load_fn(self, keys):
        _map = {obj.entity_id: obj for obj in self.hulk_relation_cls.objects.filter(entity_id__in=keys)}
        return Promise.resolve([_map.get(key) for key in keys])


class EventHulkLoader(HulkRelationLoaderBase):
    hulk_relation_cls = HulkEvent


class FigureHulkLoader(HulkRelationLoaderBase):
    hulk_relation_cls = HulkFigure


class EntryHulkLoader(HulkRelationLoaderBase):
    hulk_relation_cls = HulkEntry


class AttachmentHulkLoader(HulkRelationLoaderBase):
    hulk_relation_cls = HulkAttachment


class SourcePreviewHulkLoader(HulkRelationLoaderBase):
    hulk_relation_cls = HulkSourcePreview
