from apps.entry.models import Figure
from apps.users.roles import MONITORING_EXPERT_EDITOR, ADMIN, MONITORING_EXPERT_REVIEWER
from utils.factories import EntryFactory, FigureFactory
from utils.tests import HelixTestCase, create_user_with_role


class TestFigureModel(HelixTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(MONITORING_EXPERT_EDITOR)
        self.admin = create_user_with_role(ADMIN)
        self.entry = EntryFactory.create(created_by=self.editor)
        self.figure = FigureFactory.create(entry=self.entry, created_by=self.editor)

    def test_figure_can_be_updated_by(self):
        editor2 = create_user_with_role(MONITORING_EXPERT_EDITOR)
        self.assertFalse(self.figure.can_be_updated_by(editor2))
        self.assertTrue(self.figure.can_be_updated_by(self.editor))
        self.assertTrue(self.figure.can_be_updated_by(self.admin))

    def test_figure_can_be_created_by(self):
        editor2 = create_user_with_role(MONITORING_EXPERT_EDITOR)
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


class TestEntryModel(HelixTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(MONITORING_EXPERT_EDITOR)
        self.entry = EntryFactory.create(created_by=self.editor)

    def test_entry_can_be_updated_by(self):
        editor2 = create_user_with_role(MONITORING_EXPERT_EDITOR)
        self.assertFalse(self.entry.can_be_updated_by(editor2))
        reviwer = create_user_with_role(MONITORING_EXPERT_REVIEWER)
        self.assertFalse(self.entry.can_be_updated_by(reviwer))
        admin = create_user_with_role(ADMIN)
        self.assertTrue(self.entry.can_be_updated_by(admin))
