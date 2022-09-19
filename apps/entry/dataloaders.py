from django.db import models
from django.contrib.postgres.aggregates.general import StringAgg
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
                When(other_sub_type__isnull=False, then=F('other_sub_type__name')),
                When(violence_sub_type__isnull=False, then=F('violence_sub_type__name')),
                When(disaster_sub_type__isnull=False, then=F('disaster_sub_type__name')),
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


class FigureGeoLocationLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = Figure.objects.filter(
            id__in=keys
        ).annotate(
            geolocations=StringAgg('geo_locations__display_name', '; ')
        ).values('id', 'geolocations')
        batch_load = {
            item['id']: item['geolocations']
            for item in qs
        }
        return Promise.resolve([
            batch_load.get(key) for key in keys
        ])


class FigureSourcesReliability(DataLoader):
    def batch_load_fn(self, keys):
        qs = Figure.objects.filter(
            id__in=keys
        ).annotate(
            **Figure.annotate_sources_reliability()
        ).values('id', 'sources_reliability')
        batch_load = {
            item['id']: item['sources_reliability']
            for item in qs
        }
        return Promise.resolve([
            batch_load.get(key) for key in keys
        ])
