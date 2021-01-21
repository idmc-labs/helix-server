from django.test import RequestFactory

from helix.settings import RESOURCE_NUMBER
from apps.users.enums import USER_ROLE
from apps.resource.models import Resource
from apps.resource.serializers import ResourceSerializer
from utils.factories import ResourceFactory, ResourceGroupFactory, CountryFactory
from utils.tests import HelixTestCase, create_user_with_role


class TestResourceSerializer(HelixTestCase):
    def setUp(self):
        self.user = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT_EDITOR.name
        )
        self.group = ResourceGroupFactory.create(created_by=self.user)
        self.countries = CountryFactory.create_batch(2)
        self.resource = ResourceFactory.create_batch(
            RESOURCE_NUMBER - 1,
            created_by=self.user,
            group=self.group
        )
        self.factory = RequestFactory()
        self.request = self.factory.get('/graphql') 

    def test_resource_limit_creation_by_user(self):
        self.request.user = self.user
        data1 = {
            'created_by': self.user.id,
            'group': self.group.id,
            'name': 'name',
            'url': 'https://github.com',
            'countries': [country.id for country in self.countries]
        }
        serializer = ResourceSerializer(data=data1,
                                        context={'request': self.request})
        self.assertTrue(serializer.is_valid())
        serializer.save()
        data2 = {
            'created_by': self.user.id,
            'group': self.group.id,
            'name': 'namea',
            'url': 'https://github.com',
            'countries': [country.id for country in self.countries]
        }
        serializer = ResourceSerializer(data=data2,
                                        context={'request': self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
