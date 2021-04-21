from django.db import models
from promise import Promise
from promise.dataloader import DataLoader

from apps.entry.models import Figure, FigureCategory


def batch_load_fn_by_category(keys, category):
    qs = Figure.objects.filter(
        entry__in=keys
    ).order_by().values(
        'entry'
    ).annotate(
        total_category_figures=models.Sum(
            'total_figures',
            filter=models.Q(
                role=Figure.ROLE.RECOMMENDED,
                category=category,
            ),
        )
    ).values('entry', 'total_category_figures')

    batch_load = {
        item['entry']: item['total_category_figures']
        for item in qs
    }

    return Promise.resolve([
        batch_load.get(key, 0) for key in keys
    ])


class TotalIDPFigureByEntryLoader(DataLoader):
    def batch_load_fn(self, keys):
        return batch_load_fn_by_category(
            keys, FigureCategory.stock_idp_id()
        )


class TotalNDFigureByEntryLoader(DataLoader):
    def batch_load_fn(self, keys):
        return batch_load_fn_by_category(
            keys, FigureCategory.flow_new_displacement_id()
        )
