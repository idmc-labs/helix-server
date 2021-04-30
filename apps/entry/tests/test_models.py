from datetime import datetime, timedelta

from apps.users.enums import USER_ROLE
from apps.review.models import Review
from apps.entry.models import (
    Figure,
    EntryReviewer,
    FigureCategory,
)
from utils.factories import (
    EntryFactory,
    FigureFactory,
    ReviewFactory,
    ReviewCommentFactory,
    EventFactory,
    FigureCategoryFactory
)
from utils.tests import HelixTestCase, create_user_with_role


class TestFigureModel(HelixTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.event = EventFactory.create(start_date=(datetime.today() + timedelta(days=10)).strftime('%Y-%m-%d'),
                                         end_date=(datetime.today() + timedelta(days=25)).strftime('%Y-%m-%d'))
        self.entry = EntryFactory.create(created_by=self.editor, event=self.event)
        self.figure_cat = FigureCategoryFactory.create(type='FLOW')
        self.figure = FigureFactory.create(entry=self.entry, created_by=self.editor, category=self.figure_cat)

    def test_figure_can_be_updated_by(self):
        editor2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        self.assertFalse(self.figure.can_be_updated_by(editor2))
        self.assertTrue(self.figure.can_be_updated_by(self.editor))
        self.assertTrue(self.figure.can_be_updated_by(self.admin))

    def test_figure_can_be_created_by(self):
        editor2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        self.assertFalse(self.figure.can_be_created_by(editor2, self.entry))
        self.assertTrue(self.figure.can_be_created_by(self.editor, self.entry))

    def test_figure_clean_idu(self):
        data = dict(
            include_idu=False,
            excerpt_idu='   '
        )
        self.figure.save()
        self.assertFalse(self.figure.clean_idu(data, self.figure))
        data = dict(include_idu=True)
        self.figure.save()
        self.assertIn('excerpt_idu', self.figure.clean_idu(data, self.figure))

    def test_figure_saves_total_figures(self):
        figure = FigureFactory()
        figure.unit = 1
        figure.household_size = 4
        figure.reported = 10
        figure.save()
        self.assertEqual(figure.total_figures, figure.reported * figure.household_size)

    def test_figure_dates(self):
        self.event.refresh_from_db()
        data = dict(
            start_date=self.event.start_date - timedelta(days=1),
            end_date=self.event.end_date + timedelta(days=1),
        )
        self.figure.save()
        errors = Figure.validate_dates(data, self.figure)
        self.assertIn('end_date', errors)
        self.assertIn('start_date', errors)

    def test_figure_nd_filtering(self):
        ref = datetime.today()
        nd_cat = FigureCategory.flow_new_displacement_id()
        idp_cat = FigureCategory.stock_idp_id()
        f1 = FigureFactory.create(
            start_date=ref - timedelta(days=30),
            end_date=ref,
            category=nd_cat,
            role=Figure.ROLE.RECOMMENDED,
        )
        FigureFactory.create(
            start_date=ref,
            end_date=ref + timedelta(days=30),
            category=nd_cat,
            role=Figure.ROLE.RECOMMENDED,
        )
        f3 = FigureFactory.create(
            start_date=ref + timedelta(days=30),
            end_date=ref + timedelta(days=60),
            category=nd_cat,
            role=Figure.ROLE.RECOMMENDED,
        )
        f4 = FigureFactory.create(
            start_date=ref + timedelta(days=30),
            end_date=ref + timedelta(days=60),
            category=idp_cat,
            role=Figure.ROLE.RECOMMENDED,
        )

        nd = Figure.filtered_nd_figures(
            qs=Figure.objects.all(),
            start_date=None,
            end_date=None,
        )
        self.assertEqual(nd.count(), 3)
        self.assertNotIn(f4, nd)

        nd = Figure.filtered_nd_figures(
            qs=Figure.objects.all(),
            start_date=ref - timedelta(days=15),
            end_date=ref + timedelta(days=45),
        )
        self.assertEqual(nd.count(), 2)
        self.assertNotIn(f3, nd)
        self.assertNotIn(f4, nd)

        nd = Figure.filtered_nd_figures(
            qs=Figure.objects.all(),
            start_date=ref - timedelta(days=15),
            end_date=ref + timedelta(days=15),
        )
        self.assertEqual(nd.count(), 1)
        self.assertEqual(nd.first(), f1)

    def test_figure_idp_filtering(self):
        ref = datetime.today()
        nd_cat = FigureCategory.flow_new_displacement_id()
        idp_cat = FigureCategory.stock_idp_id()
        f1 = FigureFactory.create(
            start_date=ref - timedelta(days=30),
            end_date=ref,
            category=idp_cat,
            role=Figure.ROLE.RECOMMENDED,
        )
        FigureFactory.create(
            start_date=ref,
            category=idp_cat,
            role=Figure.ROLE.RECOMMENDED,
        )
        f3 = FigureFactory.create(
            start_date=ref + timedelta(days=30),
            end_date=ref + timedelta(days=60),
            category=idp_cat,
            role=Figure.ROLE.RECOMMENDED,
        )
        f4 = FigureFactory.create(
            start_date=ref + timedelta(days=1),
            end_date=ref + timedelta(days=2),
            category=nd_cat,  # THIS IS nd
            role=Figure.ROLE.RECOMMENDED,
        )

        idp = Figure.filtered_idp_figures(
            qs=Figure.objects.all(),
            end_date=None,
        )
        self.assertEqual(idp.count(), 3)
        self.assertNotIn(f4, idp)

        idp = Figure.filtered_idp_figures(
            qs=Figure.objects.all(),
            end_date=ref,
        )
        self.assertEqual(idp.count(), 2)
        self.assertNotIn(f3, idp)

        idp = Figure.filtered_idp_figures(
            qs=Figure.objects.all(),
            end_date=ref - timedelta(days=1),
        )
        self.assertEqual(idp.count(), 1)
        self.assertIn(f1, idp)

        idp = Figure.filtered_idp_figures(
            qs=Figure.objects.all(),
            end_date=ref + timedelta(days=30),
        )
        self.assertEqual(idp.count(), 2)
        self.assertNotIn(f1, idp)
        self.assertNotIn(f4, idp)


class TestEntryModel(HelixTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        self.entry = EntryFactory.create(created_by=self.editor)

    def test_entry_can_be_updated_by(self):
        editor2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        self.assertFalse(self.entry.can_be_updated_by(editor2))
        reviwer = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.assertFalse(self.entry.can_be_updated_by(reviwer))
        admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.assertTrue(self.entry.can_be_updated_by(admin))

    def test_entry_get_latest_reviews(self):
        e = EntryFactory.create(created_by=self.editor)
        FigureFactory.create(entry=e)
        fields = {
            0: 'abc',
            1: 'def',
            2: 'xyz'
        }
        ReviewCommentFactory.create(entry=e)
        ReviewFactory.create(entry=e, field=fields[0], value=Review.ENTRY_REVIEW_STATUS.RED)
        r2 = ReviewFactory.create(entry=e, field=fields[0], value=Review.ENTRY_REVIEW_STATUS.GREEN)
        r3 = ReviewFactory.create(entry=e, field=fields[1], value=Review.ENTRY_REVIEW_STATUS.GREEN)
        obtained = set(e.latest_reviews)
        expected = {r3, r2}  # not r1 because it should be replaced by r2
        self.assertEqual(obtained, expected)

    def test_entry_reviewer_status_auto_updates_on_review_save(self):
        e = EntryFactory.create(created_by=self.editor)
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        e.reviewers.add(reviewer)
        assert e.reviewing.count() == 1
        assert e.reviewing.first().status == EntryReviewer.REVIEW_STATUS.TO_BE_REVIEWED
        Review.objects.create(entry=e, field='article_title',
                              value=Review.ENTRY_REVIEW_STATUS.RED,
                              created_by=reviewer)
        assert e.reviewing.first().status == EntryReviewer.REVIEW_STATUS.UNDER_REVIEW

    # TODO: Add test for pdf-generation task
