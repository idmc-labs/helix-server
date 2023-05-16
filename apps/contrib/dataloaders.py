from promise.dataloader import DataLoader
from promise import Promise
from django.db import models
from .models import Client


class ExternalClientLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = Client.objects.filter(
            clienttrackinfo__in=keys
        ).annotate(
            client_track_info=models.F('clienttrackinfo'),
        )
        batch_load = {
            item.client_track_info: item for item in qs
        }
        return Promise.resolve([
            batch_load.get(key) for key in keys
        ])
