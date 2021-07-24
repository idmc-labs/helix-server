from apps.users.enums import USER_ROLE
from apps.review.models import Review
from apps.entry.models import EntryReviewer, FigureTerm
from apps.entry.filters import EntryFilter, FigureTermFilter
from utils.tests import HelixTestCase, create_user_with_role
from utils.factories import (
    EntryFactory,
)


class TestEntryFilter(HelixTestCase):
    def test_filter_by_review_status(self):
        r1 = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT.name,
        )
        r2 = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT.name,
        )
        entry1 = EntryFactory.create()
        entry1.reviewers.set([r1, r2])

        r3 = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT.name,
        )
        entry2 = EntryFactory.create()
        entry2.reviewers.set([r1, r3])

        # entry1 is now under review
        Review.objects.create(
            entry=entry1,
            created_by=r2,
            field='field',
            value=0,
        )

        data = dict(
            review_status=[EntryReviewer.REVIEW_STATUS.TO_BE_REVIEWED.name]
        )
        fqs = EntryFilter(
            data=data
        ).qs
        self.assertEqual(fqs.count(), 1)

        data = dict(
            review_status=[EntryReviewer.REVIEW_STATUS.REVIEW_COMPLETED.name]
        )
        fqs = EntryFilter(
            data=data
        ).qs
        self.assertEqual(fqs.count(), 0)

        data = dict(
            review_status=[EntryReviewer.REVIEW_STATUS.UNDER_REVIEW.name]
        )
        fqs = EntryFilter(
            data=data
        ).qs
        self.assertEqual(fqs.count(), 1)
        self.assertEqual(fqs.first(), entry1)

        data = dict(
            review_status=[EntryReviewer.REVIEW_STATUS.SIGNED_OFF.name]
        )
        fqs = EntryFilter(
            data=data
        ).qs
        self.assertEqual(fqs.count(), 0)

        fqs = EntryFilter().qs
        self.assertEqual(fqs.count(), 2)


class TestFigureTermFilter(HelixTestCase):
    def setUp(self):
        FigureTerm.objects.all().delete()
        self.ft1 = FigureTerm.objects.create(
            is_housing_related=True,
            name='one'
        )
        self.ft2 = FigureTerm.objects.create(
            is_housing_related=False,
            name='two'
        )
        self.ft3 = FigureTerm.objects.create(
            is_housing_related=True,
            name='three'
        )
        self.ft3 = FigureTerm.objects.create(
            is_housing_related=False,
            name='one two'
        )

    def test_filter_is_housing_related(self):
        qs = FigureTermFilter(
            data=dict(is_housing_related=True)
        ).qs
        self.assertEqual(qs.count(), 2)
        self.assertListEqual(
            list(qs),
            list(FigureTerm.objects.filter(is_housing_related=True))
        )

        qs = FigureTermFilter(
            data=dict(is_housing_related=False)
        ).qs
        self.assertEqual(qs.count(), 2)
        self.assertListEqual(
            list(qs),
            list(FigureTerm.objects.filter(is_housing_related=False))
        )

    def test_filter_name(self):
        text = 'one'
        qs = FigureTermFilter(
            data=dict(name=text)
        ).qs
        self.assertEqual(qs.count(), 2)
        self.assertListEqual(
            list(qs),
            list(FigureTerm.objects.filter(name__icontains=text))
        )
        self.assertIn(self.ft3, qs)

        text = 'two'
        qs = FigureTermFilter(
            data=dict(name=text)
        ).qs
        self.assertEqual(qs.count(), 2)
        self.assertListEqual(
            list(qs),
            list(FigureTerm.objects.filter(name__icontains=text))
        )
        self.assertIn(self.ft3, qs)
