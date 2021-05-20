from datetime import datetime

from django.db import models
from django.db.models import (
    Count,
    Subquery,
    OuterRef,
    IntegerField,
)
from promise import Promise
from promise.dataloader import DataLoader

from apps.entry.models import Figure, FigureCategory


class CrisisReviewCountLoader(DataLoader):
    def batch_load_fn(self, keys: list):
        '''
        keys: [crisisId]
        '''
        from apps.crisis.models import Crisis
        from apps.entry.models import EntryReviewer

        qs = Crisis.objects.filter(
            id__in=keys
        ).annotate(
            under_review_count=Subquery(
                EntryReviewer.objects.filter(
                    entry__event__crisis=OuterRef('pk'),
                    status=EntryReviewer.REVIEW_STATUS.UNDER_REVIEW
                ).order_by().values('entry__event__crisis').annotate(c=Count('id')).values('c'),
                output_field=IntegerField()
            ),
            signed_off_count=Subquery(
                EntryReviewer.objects.filter(
                    entry__event__crisis=OuterRef('pk'),
                    status=EntryReviewer.REVIEW_STATUS.SIGNED_OFF
                ).order_by().values('entry__event__crisis').annotate(c=Count('id')).values('c'),
                output_field=IntegerField()
            ),
            review_complete_count=Subquery(
                EntryReviewer.objects.filter(
                    entry__event__crisis=OuterRef('pk'),
                    status=EntryReviewer.REVIEW_STATUS.REVIEW_COMPLETED
                ).order_by().values('entry__event__crisis').annotate(c=Count('id')).values('c'),
                output_field=IntegerField()
            ),
            to_be_reviewed_count=Subquery(
                EntryReviewer.objects.filter(
                    entry__event__crisis=OuterRef('pk'),
                    status=EntryReviewer.REVIEW_STATUS.TO_BE_REVIEWED
                ).order_by().values('entry__event__crisis').annotate(c=Count('id')).values('c'),
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
    qs = Figure.objects.select_related(
        'entry__event__crisis'
    ).filter(
        entry__event__crisis__in=keys,
        role=Figure.ROLE.RECOMMENDED,
    )
    this_year = datetime.today().year

    if category == FigureCategory.flow_new_displacement_id():
        qs = Figure.filtered_nd_figures(
            qs,
            # TODO Lets discuss on the date range
            start_date=datetime(
                year=this_year,
                month=1,
                day=1
            ),
            end_date=datetime(
                year=this_year,
                month=12,
                day=31
            )
        )
    elif category == FigureCategory.stock_idp_id():
        qs = Figure.filtered_idp_figures(
            qs,
        )

    qs = qs.order_by().values(
        'entry__event__crisis'
    ).annotate(
        _total=models.Sum(
            'total_figures',
        )
    ).values('entry__event__crisis', '_total')

    batch_load = {
        item['entry__event__crisis']: item['_total']
        for item in qs
    }

    return Promise.resolve([
        batch_load.get(key) for key in keys
    ])


class TotalIDPFigureByCrisisLoader(DataLoader):
    def batch_load_fn(self, keys):
        return batch_load_fn_by_category(
            keys,
            FigureCategory.stock_idp_id(),
        )


class TotalNDFigureByCrisisLoader(DataLoader):
    def batch_load_fn(self, keys):
        return batch_load_fn_by_category(
            keys,
            FigureCategory.flow_new_displacement_id(),
        )
