from django.db import models
from promise import Promise
from promise.dataloader import DataLoader
from django.db.models import Case, F, When, CharField

from apps.entry.models import Entry, Figure


def batch_load_fn_by_category(keys, category):
    qs = Entry.objects.filter(
        id__in=keys
    ).annotate(
        **Entry._total_figure_disaggregation_subquery()
    )

    if category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT:
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
            keys, Figure.FIGURE_CATEGORY_TYPES.IDPS
        )


class TotalNDFigureByEntryLoader(DataLoader):
    def batch_load_fn(self, keys):
        return batch_load_fn_by_category(
            keys, Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT
        )


class FigureTypologyLoader(DataLoader):
    def batch_load_fn(self, keys: list):
        qs = Figure.objects.filter(
            id__in=keys
        ).annotate(
            figure_typology=Case(
                When(event__other_sub_type__isnull=False, then=F('event__other_sub_type__name')),
                When(event__violence_sub_type__isnull=False, then=F('event__violence_sub_type__name')),
                When(event__disaster_sub_type__isnull=False, then=F('event__disaster_sub_type__name')),
                output_field=CharField(),
            )
        ).values('id', 'figure_typology')
        batch_load = {
            item['id']: item['figure_typology']
            for item in qs
        }
        return Promise.resolve([
            batch_load.get(key) for key in keys
        ])
