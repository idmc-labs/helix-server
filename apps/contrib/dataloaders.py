from promise import Promise
from promise.dataloader import DataLoader

from .models import BulkApiOperation


class BulkApiOperationSuccessListLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = BulkApiOperation.objects.filter(id__in=keys)
        _map = {}
        for pk, success_list in qs.values_list('id', 'success_list'):
            _map[pk] = success_list
        return Promise.resolve([
            _map.get(key, []) for key in keys
        ])


class BulkApiOperationFailureListLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = BulkApiOperation.objects.filter(id__in=keys)
        _map = {}
        for pk, failure_list in qs.values_list('id', 'failure_list'):
            _map[pk] = failure_list
        return Promise.resolve([
            _map.get(key, []) for key in keys
        ])
