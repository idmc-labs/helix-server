from django.test import RequestFactory

from apps.contact.models import Contact
from apps.organization.serializers import OrganizationSerializer
from utils.factories import OrganizationFactory
from utils.tests import HelixTestCase


class TestCreateOrganizationSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.data = {
            "name": "org name",
            "short_name": "org1",
            "methodology": "methods",
            "methodology": "source1",
            "contacts": [
                {
                    "designation": Contact.DESIGNATION.MR.value,
                    "first_name": "test",
                    "last_name": "last",
                    "gender": Contact.GENDER.MALE.value,
                    "job_title": "job",
                    "phone": "9989999"
                 },
            ]
        }
        self.context = dict(
            request=RequestFactory().post('/graphql')
        )

    def test_valid_serializer(self):
        serializer = OrganizationSerializer(data=self.data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        organization = serializer.save()
        self.assertEqual(organization.contacts.count(), len(self.data['contacts']))

    def test_invalid_duplicate_contacts_phone_numbers(self):
        self.data['contacts'] = self.data['contacts'][:] + self.data['contacts'][:]
        serializer = OrganizationSerializer(data=self.data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('contacts', serializer.errors)

    def test_invalid_contact_phone_already_exists(self):
        Contact.objects.create(**self.data['contacts'][0],
                               organization=OrganizationFactory())

        serializer = OrganizationSerializer(data=self.data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('contacts', serializer.errors)
        self.assertIsInstance(serializer.errors['contacts'], list)
        self.assertIn('phone', serializer.errors['contacts'][0])
