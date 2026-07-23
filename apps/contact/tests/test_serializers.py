from django.test import RequestFactory

from apps.common.enums import GENDER_TYPE
from apps.contact.models import Contact
from apps.contact.serializers import ContactSerializer
from apps.users.enums import USER_ROLE
from utils.factories import CountryFactory
from utils.tests import HelixTestCase, create_user_with_role


class TestContactSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.request = RequestFactory().post("/graphql")
        self.request.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.context = dict(request=self.request)

    def _data(self, **overrides):
        data = dict(
            designation=Contact.DESIGNATION.MR.value,
            first_name="first",
            last_name="last",
            gender=GENDER_TYPE.MALE.value,
            job_title="job",
        )
        data.update(overrides)
        return data

    def test_empty_countries_of_operation_is_rejected(self):
        serializer = ContactSerializer(data=self._data(countries_of_operation=[]), context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("countries_of_operation", serializer.errors)

    def test_missing_countries_of_operation_is_rejected(self):
        serializer = ContactSerializer(data=self._data(), context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("countries_of_operation", serializer.errors)

    def test_non_empty_countries_of_operation_is_accepted(self):
        countries = CountryFactory.create_batch(2)
        serializer = ContactSerializer(
            data=self._data(countries_of_operation=[country.id for country in countries]),
            context=self.context,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
