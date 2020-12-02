from mock import patch
from django.db.models import ProtectedError

from apps.users.enums import USER_ROLE
from utils.factories import ResourceGroupFactory, ResourceFactory
from utils.tests import HelixTestCase, create_user_with_role


class TestResourceGroupModel(HelixTestCase):
    def setUp(self):
        self.reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.group = ResourceGroupFactory.create(created_by=self.reviewer)
        ResourceFactory.create(created_by=self.reviewer,
                               group=self.group)

    def test_delete_resource_group_with_resources(self):
        try:
            self.group.is_deletable()
            self.assertFalse(True, 'Should have failed')
        except ProtectedError:
            pass

    @patch('apps.resource.models.ResourceGroup.is_deletable')
    def test_can_delete(self, is_deletable):
        self.group.can_delete()
        is_deletable.assert_called_once()
