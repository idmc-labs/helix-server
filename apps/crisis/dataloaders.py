from django.db.models import (
    Count,
    Subquery,
    OuterRef,
    IntegerField,
)
from promise import Promise
from promise.dataloader import DataLoader


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
