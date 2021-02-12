from mock import patch
from django.db.models import ProtectedError
from django.core.exceptions import ValidationError

from helix.settings import RESOURCE_NUMBER
from apps.users.enums import USER_ROLE
from apps.resource.models import Resource
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

    def test_resources_creation_by_user(self):
        Resource.objects.filter(created_by=self.reviewer).count()
        with self.assertRaises(ValidationError):
            RESOURCE_CREATED = RESOURCE_NUMBER + 1
            ResourceFactory.create_batch(RESOURCE_CREATED,
                                         created_by=self.reviewer,
                                         group=self.group)

        new_count = Resource.objects.filter(created_by=self.reviewer).count()
        self.assertEqual(new_count, RESOURCE_NUMBER)  # new resources be created

    def test_resource_update(self):
        ResourceFactory.create_batch(RESOURCE_NUMBER - 2,
                                     created_by=self.reviewer,
                                     group=self.group)
        resource = ResourceFactory.create(created_by=self.reviewer, group=self.group)
        self.assertTrue(Resource.objects.filter(id=resource.id).update(name='hari'))
        with self.assertRaises(ValidationError):
            ResourceFactory.create(created_by=self.reviewer, group=self.group)
