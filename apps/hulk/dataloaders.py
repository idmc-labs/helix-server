from collections import defaultdict

from django.db.models import Sum
from promise import Promise
from promise.dataloader import DataLoader

from .models import HulkBulkImportDataset


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


class HulkBulkImportDatasetsLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = HulkBulkImportDataset.objects.filter(bulk_import_id__in=keys).order_by("import_type")
        _map = defaultdict(list)
        for dataset in qs:
            _map[dataset.bulk_import_id].append(dataset)
        return Promise.resolve([_map.get(key, []) for key in keys])
