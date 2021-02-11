import os
from datetime import datetime, timedelta

from django.core.files.storage import default_storage

from apps.users.enums import USER_ROLE
from apps.contrib.models import SourcePreview
from apps.review.models import Review
from apps.entry.models import Figure
from utils.factories import EntryFactory, FigureFactory, ReviewFactory, ReviewCommentFactory, EventFactory
from utils.tests import HelixTestCase, create_user_with_role


class TestFigureModel(HelixTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.event = EventFactory.create(start_date=(datetime.today() + timedelta(days=10)).strftime('%Y-%m-%d'))
        self.entry = EntryFactory.create(created_by=self.editor, event=self.event)
        self.figure = FigureFactory.create(entry=self.entry, created_by=self.editor)

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
        data = dict(
            start_date=(datetime.today() + timedelta(days=12)).strftime('%Y-%m-%d'),
            end_date=(datetime.today()).strftime('%Y-%m-%d'),
        )
        self.figure.save()
        errors = Figure.clean_dates(data, self.figure)
        self.assertIn('end_date', errors)
        self.assertIn('start_date', errors)


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


class TestSourcePreviewModel(HelixTestCase):
    def test_get_pdf(self):
        if os.environ.get('GITHUB_WORKFLOW'):
            print('Skipping because wkhtmltopdf requires display...')
            return
        url = 'https://github.com/JazzCore/python-pdfkit/'
        preview = SourcePreview.get_pdf(url)
        self.assertIn('.pdf', preview.pdf.name)
        self.assertTrue(default_storage.exists(preview.pdf.name))
        # again
        preview2 = SourcePreview.get_pdf(url, preview)
        self.assertTrue(os.path.exists(preview2.pdf.name))
        self.assertFalse(default_storage.exists(preview.pdf.name))
