from django.test import RequestFactory

from apps.organization.models import Organization
from apps.organization.serializers import OrganizationSerializer
from apps.users.enums import USER_ROLE
from utils.tests import HelixTestCase, create_user_with_role


class TestCreateOrganizationSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.data = {
            "name": "org name",
            "short_name": "org1",
            "methodology": "source1",
            "category": Organization.ORGANIZATION_CATEGORY.NATIONAL.value,
        }
        self.factory = RequestFactory()
        self.request = self.factory.get("/graphql")
        self.request.user = self.user = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)

    def test_valid_serializer(self):
        serializer = OrganizationSerializer(data=self.data, context={"request": self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)

        serializer.save()

    def test_category_is_required(self):
        self.data.pop("category")
        serializer = OrganizationSerializer(data=self.data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("category", serializer.errors)

    def test_methodology_cannot_be_blank(self):
        self.data["methodology"] = ""
        serializer = OrganizationSerializer(data=self.data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("methodology", serializer.errors)
