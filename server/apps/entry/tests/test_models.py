from apps.users.roles import MONITORING_EXPERT_EDITOR, ADMIN, MONITORING_EXPERT_REVIEWER
from utils.factories import EntryFactory
from utils.tests import HelixTestCase, create_user_with_role


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
