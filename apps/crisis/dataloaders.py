from django.db import models
from promise import Promise
from promise.dataloader import DataLoader

from apps.entry.models import Figure
from apps.crisis.models import Crisis
from apps.event.models import Event


def batch_load_fn_by_category(keys, category):
    qs = Crisis.objects.filter(
        id__in=keys
    ).annotate(
        **Crisis._total_figure_disaggregation_subquery()
    )

    if category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT:
        qs = qs.annotate(_total=models.F(Crisis.ND_FIGURES_ANNOTATE))
    else:
        qs = qs.annotate(_total=models.F(Crisis.IDP_FIGURES_ANNOTATE))

    batch_load = {
        item['id']: item['_total']
        for item in qs.values('id', '_total')
    }

    return Promise.resolve([
        batch_load.get(key) for key in keys
    ])


class TotalIDPFigureByCrisisLoader(DataLoader):
    def batch_load_fn(self, keys):
        return batch_load_fn_by_category(
            keys,
            Figure.FIGURE_CATEGORY_TYPES.IDPS.value,
        )


class TotalNDFigureByCrisisLoader(DataLoader):
    def batch_load_fn(self, keys):
        return batch_load_fn_by_category(
            keys,
            Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value,
        )


class EventCountLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = Crisis.objects.filter(
            id__in=keys
        ).annotate(
            event_count=models.Subquery(
                Event.objects.filter(
                    crisis=models.OuterRef('pk')
                ).order_by().values('crisis').annotate(
                    count=models.Count('crisis')
                ).values('count')[:1],
                output_field=models.IntegerField()
            )
        )
        batch_load = {
            item['id']: item['event_count']
            for item in qs.values('id', 'event_count')
        }
        return Promise.resolve([
            batch_load.get(key) for key in keys
        ])


class CrisisReviewCountLoader(DataLoader):
    def batch_load_fn(self, keys: list):
        qs = Crisis.objects.filter(
            id__in=keys
        ).annotate(
            **Crisis.annotate_review_figures_count()
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
