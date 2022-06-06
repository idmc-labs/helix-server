from django.db import models
from django.db.models import (
    Count,
    Subquery,
    OuterRef,
    IntegerField,
)
from promise import Promise
from promise.dataloader import DataLoader

from apps.entry.models import Figure, EntryReviewer
from apps.crisis.models import Crisis
from apps.event.models import Event


class CrisisReviewCountLoader(DataLoader):
    def batch_load_fn(self, keys: list):
        '''
        keys: [crisisId]
        '''
        qs = Crisis.objects.filter(
            id__in=keys
        ).annotate(
            under_review_count=Subquery(
                Figure.objects.filter(
                    event__crisis=OuterRef('pk'),
                    entry__review_status=EntryReviewer.REVIEW_STATUS.UNDER_REVIEW
                ).order_by().values('event__crisis').annotate(c=Count('id')).values('c'),
                output_field=IntegerField()
            ),
            signed_off_count=Subquery(
                Figure.objects.filter(
                    event__crisis=OuterRef('pk'),
                    entry__review_status=EntryReviewer.REVIEW_STATUS.SIGNED_OFF
                ).order_by().values('event__crisis').annotate(c=Count('id')).values('c'),
                output_field=IntegerField()
            ),
            review_complete_count=Subquery(
                Figure.objects.filter(
                    event__crisis=OuterRef('pk'),
                    entry__review_status=EntryReviewer.REVIEW_STATUS.REVIEW_COMPLETED
                ).order_by().values('event__crisis').annotate(c=Count('id')).values('c'),
                output_field=IntegerField()
            ),
            to_be_reviewed_count=Subquery(
                Figure.objects.filter(
                    event__crisis=OuterRef('pk'),
                    entry__review_status=EntryReviewer.REVIEW_STATUS.TO_BE_REVIEWED
                ).order_by().values('event__crisis').annotate(c=Count('id')).values('c'),
                output_field=IntegerField()
            ),
        ).values(
            'id', 'under_review_count', 'signed_off_count',
            'review_complete_count', 'to_be_reviewed_count',
        )

        list_to_dict = {
            item['id']: {
                'under_review_count': item['under_review_count'],
                'signed_off_count': item['signed_off_count'],
                'review_complete_count': item['review_complete_count'],
                'to_be_reviewed_count': item['to_be_reviewed_count'],
            }
            for item in qs
        }

        return Promise.resolve([
            list_to_dict.get(crisis_id, dict())
            for crisis_id in keys
        ])


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
