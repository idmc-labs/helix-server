from datetime import datetime, timedelta

from django.utils import timezone

from apps.crisis.models import Crisis
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
    ReviewCommentFactory,
    EventFactory,
    FigureCategoryFactory
)
from utils.tests import HelixTestCase, create_user_with_role


class TestFigureModel(HelixTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.event = EventFactory.create(start_date=(timezone.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
                                         end_date=(timezone.now() + timedelta(days=25)).strftime('%Y-%m-%d'))
        self.entry = EntryFactory.create(created_by=self.editor, event=self.event)
        self.figure_cat = FigureCategoryFactory.create(type='FLOW')
        self.figure = FigureFactory.create(entry=self.entry, created_by=self.editor, category=self.figure_cat)

    def test_figure_can_be_updated_by(self):
        editor2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.assertTrue(self.figure.can_be_updated_by(editor2))
        self.assertTrue(self.figure.can_be_updated_by(self.editor))
        self.assertTrue(self.figure.can_be_updated_by(self.admin))

    def test_figure_can_be_created_by(self):
        editor2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.assertTrue(self.figure.can_be_created_by(editor2, self.entry))
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

    def test_figure_nd_filtering(self):
        ref = datetime.today()
        FigureCategory._invalidate_category_ids_cache()
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
            end_date=ref + timedelta(days=360),
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
        FigureCategory._invalidate_category_ids_cache()
        # TODO: Add test for DISASTER as well, once the logic arrives
        event = EventFactory.create(event_type=Crisis.CRISIS_TYPE.CONFLICT)
        entry = EntryFactory.create(event=event)
        nd_cat = FigureCategory.flow_new_displacement_id()
        idp_cat = FigureCategory.stock_idp_id()
        f1 = FigureFactory.create(
            entry=entry,
            start_date=ref - timedelta(days=30),
            end_date=ref,
            category=idp_cat,
            role=Figure.ROLE.RECOMMENDED,
        )
        FigureFactory.create(
            entry=entry,
            start_date=ref,
            end_date=None,
            category=idp_cat,
            role=Figure.ROLE.RECOMMENDED,
        )
        f3 = FigureFactory.create(
            entry=entry,
            start_date=ref + timedelta(days=30),
            end_date=ref + timedelta(days=60),
            category=idp_cat,
            role=Figure.ROLE.RECOMMENDED,
        )
        f4 = FigureFactory.create(
            entry=entry,
            start_date=ref + timedelta(days=1),
            end_date=ref + timedelta(days=2),
            category=nd_cat,  # THIS IS nd
            role=Figure.ROLE.RECOMMENDED,
        )

        idp = Figure.filtered_idp_figures(
            qs=Figure.objects.all(),
            end_date=ref,
        )
        self.assertEqual(idp.count(), 2)
        self.assertNotIn(f4, idp)
        self.assertNotIn(f3, idp)

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
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.entry = EntryFactory.create(created_by=self.editor)

    def test_entry_can_be_updated_by(self):
        editor2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.assertTrue(self.entry.can_be_updated_by(editor2))
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
        ReviewCommentFactory.create(entry=e, created_by=self.editor)
        Review.objects.create(entry=e, created_by=self.editor, field=fields[0], value=Review.ENTRY_REVIEW_STATUS.RED)
        r2 = Review.objects.create(entry=e, created_by=self.editor, field=fields[0], value=Review.ENTRY_REVIEW_STATUS.GREEN)
        r3 = Review.objects.create(entry=e, created_by=self.editor, field=fields[1], value=Review.ENTRY_REVIEW_STATUS.GREEN)
        obtained = set(e.latest_reviews)
        expected = {r3, r2}  # not r1 because it should be replaced by r2
        self.assertEqual(obtained, expected)

    def test_entry_reviewer_status_auto_updates_on_review_save(self):
        e = EntryFactory.create(created_by=self.editor)
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        e.reviewers.add(reviewer)
        assert e.reviewing.count() == 1
        assert e.reviewing.first().status == EntryReviewer.REVIEW_STATUS.TO_BE_REVIEWED
        Review.objects.create(entry=e, field='article_title',
                              value=Review.ENTRY_REVIEW_STATUS.RED,
                              created_by=reviewer)
        assert e.reviewing.first().status == EntryReviewer.REVIEW_STATUS.UNDER_REVIEW

        # try clearing the reviewers
        e.reviewers.clear()
        # should change the entry review_status
        e.refresh_from_db()
        assert e.review_status is None

        # manually create entry reviewer
        e_r = EntryReviewer.objects.create(
            entry=e,
            reviewer=reviewer
        )
        e.refresh_from_db()
        assert e.review_status == EntryReviewer.REVIEW_STATUS.TO_BE_REVIEWED
        # change the status
        e_r.status = EntryReviewer.REVIEW_STATUS.UNDER_REVIEW
        e_r.save()
        e.refresh_from_db()
        assert e.review_status == EntryReviewer.REVIEW_STATUS.UNDER_REVIEW
        # delete the instance
        e_r.delete()
        e.refresh_from_db()
        assert e.review_status is None

    def test_entry_review_status_change_on_reviewer_status_change(self):
        e = EntryFactory.create(created_by=self.editor)
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        reviewer2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        assert e.review_status is None
        e.reviewers.add(reviewer)
        e.reviewers.add(reviewer2)

        e.refresh_from_db()
        assert e.review_status == EntryReviewer.REVIEW_STATUS.TO_BE_REVIEWED

        Review.objects.create(entry=e, field='article_title',
                              value=Review.ENTRY_REVIEW_STATUS.RED,
                              created_by=reviewer)
        assert e.reviewing.first().status == EntryReviewer.REVIEW_STATUS.UNDER_REVIEW

        e.refresh_from_db()
        assert e.review_status == EntryReviewer.REVIEW_STATUS.UNDER_REVIEW
        Review.objects.create(entry=e, field='article_title',
                              value=Review.ENTRY_REVIEW_STATUS.RED,
                              created_by=reviewer2)
        e.refresh_from_db()
        assert e.review_status == EntryReviewer.REVIEW_STATUS.UNDER_REVIEW
        review = EntryReviewer.objects.get(
            entry=e,
            reviewer=reviewer
        )
        review.status = EntryReviewer.REVIEW_STATUS.REVIEW_COMPLETED
        review.save()

        e.refresh_from_db()
        assert e.review_status == EntryReviewer.REVIEW_STATUS.REVIEW_COMPLETED

    def test_text_field_should_accept_markup_and_speicial_should_remove_html_tags(self):
        html_data = '<html><body><h2>test</h2><p> test</p><p id="demo"> test</p><script></script></body></html>'
        markup_text = """
        # H1 heading 1
        ## H2 heading 2
        ### H3 heading 3
        **bold text**
        *italicized text*
        > blockquote
        1. First item
        2. Second item
        3. Third item
        - First item
        - Second item
        - Third item
        `code`
        ---
        [title](https://www.example.com)
        ![alt text](image.jpg)
        """
        e = EntryFactory.create(created_by=self.editor)
        e.source_excerpt = html_data
        e.calculation_logic = '~!@#$%^&*<>?/'
        e.article_title = markup_text
        e.save()
        e.refresh_from_db()

        self.assertEqual(e.source_excerpt, 'test test test')
        self.assertEqual(e.calculation_logic, '~!@#$%^&*<>?/')
        self.assertEqual(e.article_title, markup_text)

        markup_and_html_mixed_data = """
        # H1 heading 1
        ## H2 heading 2
        ### H3 heading 3
        **bold text**
        *italicized text*
        > blockquote
        1. <html><body><p>First item</p><script></script></body></html>
        2. <h1>Second item</h1>
        3. <div><p>Third item</p></div>
        - <li>First item</li>
        - <li>Second item</li>
        - <li>Third item</li>
        `code`
        ---
        [title](https://www.example.com)
        ![alt text](image.jpg)
        <script>console.log("test")</script>
        """
        markup_and_html_mixed_data_cleaned = """
        # H1 heading 1
        ## H2 heading 2
        ### H3 heading 3
        **bold text**
        *italicized text*
        > blockquote
        1. First item
        2. Second item
        3. Third item
        - <li>First item</li>
        - <li>Second item</li>
        - <li>Third item</li>
        `code`
        ---
        [title](https://www.example.com)
        ![alt text](image.jpg)
        console.log("test")
        """

        e.calculation_logic = markup_and_html_mixed_data
        e.save()
        e.refresh_from_db()
        self.assertEqual(e.calculation_logic, markup_and_html_mixed_data_cleaned)


class TestCloneEntry(HelixTestCase):
    def test_clone_relevant_fields_only(self):
        user = create_user_with_role(USER_ROLE.ADMIN.name)
        event = EventFactory.create()
        entry = EntryFactory.create(
            created_by=user,
            event=event,
        )

        # lets clone to following events
        new_events = EventFactory.create_batch(3)
        duplicated_entries = entry.clone_across_events(new_events)

        self.assertEqual(len(new_events), len(duplicated_entries))
        self.assertNotIn(event.id,
                         [each['event'] for each in duplicated_entries])
        self.assertEqual(
            {None},
            set([each.get('id') for each in duplicated_entries])
        )
        self.assertEqual(
            {None},
            set([each.get('created_by') for each in duplicated_entries])
        )
        self.assertEqual(
            {None},
            set([each.get('created_at') for each in duplicated_entries])
        )
        self.assertEqual(
            1,
            len(set([each.get('article_title') for each in duplicated_entries]))
        )
        self.assertIsNotNone(duplicated_entries[0].get('article_title'))
