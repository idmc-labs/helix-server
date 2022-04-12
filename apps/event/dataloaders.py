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
from apps.event.models import Event


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


class EventReviewCountLoader(DataLoader):
    def batch_load_fn(self, keys: list):
        '''
        keys: [entryId]
        '''
        qs = Event.objects.filter(
            id__in=keys
        ).annotate(
            under_review_count=Subquery(
                Figure.objects.filter(
                    event=OuterRef('pk'),
                    entry__review_status=EntryReviewer.REVIEW_STATUS.UNDER_REVIEW
                ).order_by().values('event').annotate(c=Count('id')).values('c'),
                output_field=IntegerField()
            ),
            signed_off_count=Subquery(
                Figure.objects.filter(
                    event=OuterRef('pk'),
                    entry__review_status=EntryReviewer.REVIEW_STATUS.SIGNED_OFF
                ).order_by().values('event').annotate(c=Count('id')).values('c'),
                output_field=IntegerField()
            ),
            review_complete_count=Subquery(
                Figure.objects.filter(
                    event=OuterRef('pk'),
                    entry__review_status=EntryReviewer.REVIEW_STATUS.REVIEW_COMPLETED
                ).order_by().values('event').annotate(c=Count('id')).values('c'),
                output_field=IntegerField()
            ),
            to_be_reviewed_count=Subquery(
                Figure.objects.filter(
                    event=OuterRef('pk'),
                    entry__review_status=EntryReviewer.REVIEW_STATUS.TO_BE_REVIEWED
                ).order_by().values('event').annotate(c=Count('id')).values('c'),
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
            list_to_dict.get(event_id, dict())
            for event_id in keys
        ])


class EventEntryCountLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = Event.objects.filter(
            id__in=keys
        ).annotate(entry_count=Count('figures__entries', distinct=True))

        batch_load = {
            item['id']: item['entry_count']
            for item in qs.values('id', 'entry_count')
        }
        return Promise.resolve([
            batch_load.get(key) for key in keys
        ])
