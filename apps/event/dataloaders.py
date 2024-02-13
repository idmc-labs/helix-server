from collections import defaultdict
from django.db import models
from django.db.models import Case, F, When, CharField
from django.contrib.postgres.aggregates import ArrayAgg

from promise import Promise
from promise.dataloader import DataLoader

from apps.entry.models import Figure
from apps.event.models import Event, EventCode


def batch_load_fn_by_category(keys, category):
    qs = Event.objects.filter(
        id__in=keys
    ).annotate(
        **Event._total_figure_disaggregation_subquery()
    )

    if category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value:
        qs = qs.annotate(_total=models.F(Event.ND_FIGURES_ANNOTATE))
    else:
        qs = qs.annotate(_total=models.F(Event.IDP_FIGURES_ANNOTATE))

    batch_load = {
        item['id']: item['_total']
        for item in qs.values('id', '_total')
    }

    return Promise.resolve([
        batch_load.get(key) for key in keys
    ])


class TotalIDPFigureByEventLoader(DataLoader):
    def batch_load_fn(self, keys):
        return batch_load_fn_by_category(
            keys,
            Figure.FIGURE_CATEGORY_TYPES.IDPS.value,
        )


class TotalNDFigureByEventLoader(DataLoader):
    def batch_load_fn(self, keys):
        return batch_load_fn_by_category(
            keys,
            Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value,
        )


class MaxStockIDPFigureEndDateByEventLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = Event.objects.filter(
            id__in=keys
        ).annotate(
            **Event._total_figure_disaggregation_subquery()
        )
        batch_load = {
            item['id']: item[Event.IDP_FIGURES_REFERENCE_DATE_ANNOTATE]
            for item in qs.values('id', Event.IDP_FIGURES_REFERENCE_DATE_ANNOTATE)
        }
        return Promise.resolve([
            batch_load.get(key) for key in keys
        ])


class EventEntryCountLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = Event.objects.filter(
            id__in=keys
        ).annotate(
            entry_count=models.Subquery(
                Figure.objects.filter(
                    event=models.OuterRef('pk')
                ).order_by().values('event').annotate(
                    count=models.Count('entry', distinct=True)
                ).values('count')[:1],
                output_field=models.IntegerField()
            )
        )
        batch_load = {
            item['id']: item['entry_count']
            for item in qs.values('id', 'entry_count')
        }
        return Promise.resolve([
            batch_load.get(key) for key in keys
        ])


class EventTypologyLoader(DataLoader):
    def batch_load_fn(self, keys: list):
        qs = Event.objects.filter(
            id__in=keys
        ).annotate(
            event_typology=Case(
                When(other_sub_type__isnull=False, then=F('other_sub_type__name')),
                When(violence_sub_type__isnull=False, then=F('violence_sub_type__name')),
                When(disaster_sub_type__isnull=False, then=F('disaster_sub_type__name')),
                output_field=CharField(),
            )
        ).values('id', 'event_typology')
        batch_load = {
            item['id']: item['event_typology']
            for item in qs
        }
        return Promise.resolve([
            batch_load.get(key) for key in keys
        ])


class EventFigureTypologyLoader(DataLoader):
    def batch_load_fn(self, keys: list):
        qs = Figure.objects.filter(
            event_id__in=keys
        ).values(
            'event_id'
        ).annotate(
            event_typology=ArrayAgg(Case(
                When(other_sub_type__isnull=False, then=F('other_sub_type__name')),
                When(violence_sub_type__isnull=False, then=F('violence_sub_type__name')),
                When(disaster_sub_type__isnull=False, then=F('disaster_sub_type__name')),
                output_field=CharField(),
            ), distinct=True)
        )
        batch_load = {
            item['event_id']: item['event_typology']
            for item in qs
        }
        return Promise.resolve([
            batch_load.get(key) for key in keys
        ])


class EventReviewCountLoader(DataLoader):
    def batch_load_fn(self, keys: list):
        qs = Event.objects.filter(
            id__in=keys
        ).annotate(
            **Event.annotate_review_figures_count()
        ).values(
            'id',
            'review_not_started_count',
            'review_in_progress_count',
            'review_re_request_count',
            'review_approved_count',
            'total_count',
            'progress',
        )
        batch_load = {
            item['id']: {
                'review_not_started_count': item['review_not_started_count'],
                'review_in_progress_count': item['review_in_progress_count'],
                'review_re_request_count': item['review_re_request_count'],
                'review_approved_count': item['review_approved_count'],
                'total_count': item['total_count'],
                'progress': item['progress'],
            } for item in qs
        }
        return Promise.resolve([
            batch_load.get(key) for key in keys
        ])


class EventCodeLoader(DataLoader):
    def batch_load_fn(self, keys: list):
        qs = EventCode.objects.filter(event__id__in=keys)
        _map = defaultdict(list)
        for event_code in qs.all():
            _map[event_code.event_id].append(event_code)
        return Promise.resolve([_map.get(key) for key in keys])


class EventCrisisLoader(DataLoader):
    def batch_load_fn(self, keys: list):
        qs = Event.objects.filter(id__in=keys).select_related('crisis').only('id', 'crisis')
        _map = {}
        for event in qs.all():
            _map[event.id] = event.crisis
        return Promise.resolve([_map.get(key) for key in keys])
