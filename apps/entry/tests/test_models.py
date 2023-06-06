from datetime import datetime, timedelta

from django.utils import timezone

from apps.crisis.models import Crisis
from apps.users.enums import USER_ROLE
from apps.entry.models import (
    Figure,
)
from utils.factories import (
    EntryFactory,
    FigureFactory,
    EventFactory,
)
from utils.tests import HelixTestCase, create_user_with_role


class TestFigureModel(HelixTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.event = EventFactory.create(
            start_date=(timezone.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
            end_date=(timezone.now() + timedelta(days=25)).strftime('%Y-%m-%d'),
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
        self.entry = EntryFactory.create(created_by=self.editor,)
        self.figure_cat = Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT
        self.figure = FigureFactory.create(
            entry=self.entry, created_by=self.editor, category=self.figure_cat, event=self.event
        )

    def test_figure_nd_filtering(self):
        ref = datetime(year=2022, month=6, day=1)
        nd_cat = Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value
        idp_cat = Figure.FIGURE_CATEGORY_TYPES.IDPS.value

        f0 = FigureFactory.create(
            start_date=ref - timedelta(days=300),
            end_date=ref + timedelta(days=100),
            category=nd_cat,
            role=Figure.ROLE.RECOMMENDED,
            event=self.event,
        )
        f1 = FigureFactory.create(
            start_date=ref - timedelta(days=300),
            end_date=ref + timedelta(days=300),
            category=nd_cat,
            role=Figure.ROLE.RECOMMENDED,
            event=self.event,
        )
        f2 = FigureFactory.create(
            start_date=ref,
            end_date=ref + timedelta(days=30),
            category=nd_cat,
            role=Figure.ROLE.RECOMMENDED,
            event=self.event,
        )
        f3 = FigureFactory.create(
            start_date=ref + timedelta(days=30),
            end_date=ref + timedelta(days=60),
            category=nd_cat,
            role=Figure.ROLE.RECOMMENDED,
            event=self.event,
        )
        f4 = FigureFactory.create(
            start_date=ref + timedelta(days=30),
            end_date=ref + timedelta(days=60),
            category=idp_cat,
            role=Figure.ROLE.RECOMMENDED,
            event=self.event,
        )

        nd = Figure.filtered_nd_figures(
            qs=Figure.objects.all(),
            start_date=ref,
            end_date=ref + timedelta(days=400),
        )
        self.assertEqual(nd.count(), 4)
        self.assertIn(f0, nd)
        self.assertIn(f1, nd)
        self.assertIn(f2, nd)
        self.assertIn(f3, nd)
        self.assertNotIn(f4, nd)

        nd = Figure.filtered_nd_figures(
            qs=Figure.objects.all(),
            start_date=ref,
            end_date=ref + timedelta(days=100),
        )
        self.assertEqual(nd.count(), 3)
        self.assertIn(f0, nd)
        self.assertNotIn(f1, nd)
        self.assertIn(f2, nd)
        self.assertIn(f3, nd)
        self.assertNotIn(f4, nd)

        nd = Figure.filtered_nd_figures(
            qs=Figure.objects.all(),
            start_date=ref - timedelta(days=15),
            end_date=ref + timedelta(days=60),
        )
        self.assertEqual(nd.count(), 2)
        self.assertNotIn(f0, nd)
        self.assertNotIn(f1, nd)
        self.assertIn(f2, nd)
        self.assertIn(f3, nd)
        self.assertNotIn(f4, nd)

        nd = Figure.filtered_nd_figures(
            qs=Figure.objects.all(),
            start_date=ref - timedelta(days=15),
            end_date=ref + timedelta(days=45),
        )
        self.assertEqual(nd.count(), 2)
        self.assertNotIn(f0, nd)
        self.assertNotIn(f1, nd)
        self.assertIn(f2, nd)
        self.assertIn(f3, nd)
        self.assertNotIn(f4, nd)

        nd = Figure.filtered_nd_figures(
            qs=Figure.objects.all(),
            start_date=ref - timedelta(days=15),
            end_date=ref + timedelta(days=15),
        )
        self.assertNotIn(f0, nd)
        self.assertNotIn(f1, nd)
        self.assertIn(f2, nd)
        self.assertNotIn(f3, nd)
        self.assertNotIn(f4, nd)

    def test_figure_idp_filtering(self):
        ref = datetime(year=2022, month=6, day=1)
        event = EventFactory.create(event_type=Crisis.CRISIS_TYPE.CONFLICT)

        entry = EntryFactory.create()
        nd_cat = Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT
        idp_cat = Figure.FIGURE_CATEGORY_TYPES.IDPS

        f1 = FigureFactory.create(
            entry=entry,
            start_date=ref - timedelta(days=30),
            end_date=ref,
            category=idp_cat,
            role=Figure.ROLE.RECOMMENDED,
            event=event,
        )
        f2 = FigureFactory.create(
            entry=entry,
            start_date=ref,
            end_date=ref + timedelta(days=365),
            category=idp_cat,
            role=Figure.ROLE.RECOMMENDED,
            event=event,
        )
        f3 = FigureFactory.create(
            entry=entry,
            start_date=ref + timedelta(days=30),
            end_date=ref + timedelta(days=60),
            category=idp_cat,
            role=Figure.ROLE.RECOMMENDED,
            event=event,
        )
        f4 = FigureFactory.create(
            entry=entry,
            start_date=ref + timedelta(days=10),
            end_date=ref + timedelta(days=20),
            category=idp_cat,
            role=Figure.ROLE.RECOMMENDED,
            event=event,
        )
        f5 = FigureFactory.create(
            entry=entry,
            start_date=ref + timedelta(days=1),
            end_date=ref + timedelta(days=2),
            category=nd_cat,  # THIS IS nd
            role=Figure.ROLE.RECOMMENDED,
            event=event,
        )

        idp = Figure.filtered_idp_figures(
            qs=Figure.objects.all(),
            start_date=ref,
            end_date=ref,
        )
        self.assertEqual(idp.count(), 1)
        self.assertIn(f1, idp)
        self.assertNotIn(f2, idp)
        self.assertNotIn(f3, idp)
        self.assertNotIn(f4, idp)
        self.assertNotIn(f5, idp)
        idp = Figure.filtered_idp_figures_for_listing(
            qs=Figure.objects.all(),
            start_date=ref,
            end_date=ref,
        )
        self.assertEqual(idp.count(), 1)
        self.assertIn(f1, idp)
        self.assertNotIn(f2, idp)
        self.assertNotIn(f3, idp)
        self.assertNotIn(f4, idp)
        self.assertNotIn(f5, idp)

        idp = Figure.filtered_idp_figures(
            qs=Figure.objects.all(),
            start_date=ref - timedelta(days=1),
            end_date=ref,
        )
        self.assertEqual(idp.count(), 1)
        self.assertIn(f1, idp)
        self.assertNotIn(f2, idp)
        self.assertNotIn(f3, idp)
        self.assertNotIn(f4, idp)
        self.assertNotIn(f5, idp)
        idp = Figure.filtered_idp_figures_for_listing(
            qs=Figure.objects.all(),
            start_date=ref - timedelta(days=1),
            end_date=ref,
        )
        self.assertEqual(idp.count(), 1)
        self.assertIn(f1, idp)
        self.assertNotIn(f2, idp)
        self.assertNotIn(f3, idp)
        self.assertNotIn(f4, idp)
        self.assertNotIn(f5, idp)

        idp = Figure.filtered_idp_figures(
            qs=Figure.objects.all(),
            start_date=ref,
            end_date=ref + timedelta(days=30),
        )
        self.assertEqual(idp.count(), 0)
        self.assertNotIn(f1, idp)
        self.assertNotIn(f2, idp)
        self.assertNotIn(f3, idp)
        self.assertNotIn(f4, idp)
        self.assertNotIn(f5, idp)
        idp = Figure.filtered_idp_figures_for_listing(
            qs=Figure.objects.all(),
            start_date=ref,
            end_date=ref + timedelta(days=30),
        )
        self.assertEqual(idp.count(), 2)
        self.assertIn(f1, idp)
        self.assertNotIn(f2, idp)
        self.assertNotIn(f3, idp)
        self.assertIn(f4, idp)
        self.assertNotIn(f5, idp)


class TestEntryModel(HelixTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.entry = EntryFactory.create(created_by=self.editor)
        self.event = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )

    def test_text_field_should_accept_markup_and_speicial_should_remove_html_tags(self):
        html_data = '<html><body><h2>test</h2><p>test</p><p id="demo">test</p><script></script></body></html>'
        e = FigureFactory.create(created_by=self.editor, event=self.event,)
        e.source_excerpt = html_data
        e.calculation_logic = '~!@#$%^&*<>?/'
        e.save()
        e.refresh_from_db()

        self.assertEqual(e.source_excerpt, "\ntest\ntest\ntest")
        self.assertEqual(e.calculation_logic, '~!@#$%^&*<>?/')

        markup_and_html_mixed_data = """
        # H1 heading 1
        ## H2 heading 2
        ### H3 heading 3
        **bold text**
        *italicized text*
        > blockquote
        1. <html><body>First item<script></script></body></html>
        2. Second item
        3. Third item
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
        print('\n\n\n\n', e.calculation_logic, '\n\n\n\n')
        print('\n\n\n\n', markup_and_html_mixed_data_cleaned, '\n\n\n\n')
        self.assertEqual(e.calculation_logic, markup_and_html_mixed_data_cleaned)
