from django.test import RequestFactory

from apps.organization.serializers import OrganizationSerializer
from utils.tests import HelixTestCase, create_user_with_role
from apps.users.enums import USER_ROLE


class TestCreateOrganizationSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.data = {
            "name": "org name",
            "short_name": "org1",
            "methodology": "source1",
        }
        self.factory = RequestFactory()
        self.request = self.factory.get('/graphql')
        self.request.user = self.user = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)

    def test_valid_serializer(self):
        serializer = OrganizationSerializer(data=self.data, context={'request': self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)

        serializer.save()
