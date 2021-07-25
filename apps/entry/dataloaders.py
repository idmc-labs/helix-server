from django.db import models
from promise import Promise
from promise.dataloader import DataLoader

from apps.entry.models import Entry, FigureCategory


def batch_load_fn_by_category(keys, category):
    qs = Entry.objects.filter(
        id__in=keys
    ).annotate(
        **Entry._total_figure_disaggregation_subquery()
    )

    if category == FigureCategory.flow_new_displacement_id():
        qs = qs.annotate(_total=models.F(Entry.ND_FIGURES_ANNOTATE))
    else:
        qs = qs.annotate(_total=models.F(Entry.IDP_FIGURES_ANNOTATE))

    batch_load = {
        item['id']: item['_total']
        for item in qs.values('id', '_total')
    }

    return Promise.resolve([
        batch_load.get(key) for key in keys
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
