import json

from apps.users.enums import USER_ROLE
from utils.factories import (
    CommunicationFactory,
    CommunicationMediumFactory,
    ContactFactory,
    CountryFactory,
    OrganizationFactory,
)
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestCreateContact(HelixGraphQLTestCase):
    def setUp(self) -> None:
        countries = CountryFactory.create_batch(2)
        organization = OrganizationFactory.create()
        self.mutation = """
        mutation CreateContact($input: ContactCreateInputType!) {
            createContact(data: $input) {
                ok
                errors
                result {
                    countriesOfOperation {
                        id
                        name
                    }
                    id
                    firstName
                    lastName
                    organization {
                        id
                        shortName
                    }
                    jobTitle
                    gender
                    designation
                    createdAt
                }
            }
        }
        """
        self.input = {
            "designation": "MS",
            "firstName": "first",
            "lastName": "last",
            "gender": "MALE",
            "jobTitle": "dev",
            "organization": str(organization.id),
            "countriesOfOperation": [each.id for each in countries],
        }

    def test_valid_contact_creation(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(self.mutation, input_data=self.input)

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content["data"]["createContact"]["ok"], content)
        self.assertEqual(content["data"]["createContact"]["result"]["firstName"], self.input["firstName"])
        self.assertEqual(content["data"]["createContact"]["result"]["organization"]["id"], self.input["organization"])
        self.assertEqual(
            len(content["data"]["createContact"]["result"]["countriesOfOperation"]), len(self.input["countriesOfOperation"])
        )

    def test_invalid_contact_creation_by_guest(self) -> None:
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(self.mutation, input_data=self.input)

        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content["errors"][0]["message"])


class TestUpdateContact(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.contact = ContactFactory.create()
        self.mutation = """
        mutation UpdateContact($input: ContactUpdateInputType!) {
            updateContact(data: $input) {
                ok
                errors
                result {
                    firstName
                    lastName
                    organization {
                        id
                        shortName
                    }
                }
            }
        }
        """
        self.input = {
            "id": self.contact.id,
            "firstName": "new name",
        }

    def test_valid_contact_update(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(self.mutation, input_data=self.input)

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content["data"]["updateContact"]["ok"], content)
        self.assertEqual(content["data"]["updateContact"]["result"]["firstName"], self.input["firstName"])
        self.assertEqual(content["data"]["updateContact"]["result"]["lastName"], self.contact.last_name)

    def test_invalid_contact_update_by_guest(self) -> None:
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(self.mutation, input_data=self.input)

        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content["errors"][0]["message"])


class TestDeleteContact(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.contact = ContactFactory.create()
        self.mutation = """
        mutation DeleteContact($id: ID!) {
            deleteContact(id: $id) {
                ok
                errors
                result {
                    id
                }
            }
        }
        """
        self.variables = {
            "id": str(self.contact.id),
        }

    def test_valid_contact_delete(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(self.mutation, variables=self.variables)

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content["data"]["deleteContact"]["ok"], content)
        self.assertEqual(content["data"]["deleteContact"]["result"]["id"], self.variables["id"])

    def test_invalid_contact_delete_by_guest(self) -> None:
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(self.mutation, variables=self.variables)

        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content["errors"][0]["message"])


class TestCommunication(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.mutation = """
        mutation MyMutation($input: CommunicationCreateInputType!) {
          createCommunication(data: $input) {
            ok
            errors
            result {
              id
              medium {
                name
              }
            }
          }
        }
        """
        self.contact = ContactFactory.create()
        self.country = CountryFactory.create()
        self.medium = CommunicationMediumFactory.create()
        self.input = {
            "contact": str(self.contact.id),
            "subject": "Subject",
            "content": "Content",
            "medium": str(self.medium.id),
            "country": self.country.id,
        }

    def test_valid_communication_creation(self):
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(self.mutation, input_data=self.input)
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertTrue(content["data"]["createCommunication"]["ok"], content)

    def test_invalid_communication_creation_by_guest(self):
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(self.mutation, input_data=self.input)
        content = response.json()
        self.assertIn(PERMISSION_DENIED_MESSAGE, content["errors"][0]["message"])


class TestUpdateCommunication(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.communication = CommunicationFactory.create()
        self.mutation = """
        mutation UpdateCommunication($input: CommunicationUpdateInputType!) {
          updateCommunication(data: $input) {
            ok
            errors
            result {
              id
              subject
            }
          }
        }
        """
        self.input = {
            "id": str(self.communication.id),
            "subject": "Updated subject",
        }

    def test_valid_communication_update(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(self.mutation, input_data=self.input)
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertTrue(content["data"]["updateCommunication"]["ok"], content)
        self.assertEqual(content["data"]["updateCommunication"]["result"]["subject"], self.input["subject"])

    def test_invalid_communication_update_by_guest(self) -> None:
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(self.mutation, input_data=self.input)
        content = response.json()
        self.assertIn(PERMISSION_DENIED_MESSAGE, content["errors"][0]["message"])


class TestDeleteCommunication(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.communication = CommunicationFactory.create()
        self.mutation = """
        mutation DeleteCommunication($id: ID!) {
          deleteCommunication(id: $id) {
            ok
            errors
            result {
              id
            }
          }
        }
        """
        self.variables = {"id": str(self.communication.id)}

    def test_valid_communication_delete(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(self.mutation, variables=self.variables)
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertTrue(content["data"]["deleteCommunication"]["ok"], content)

    def test_invalid_communication_delete_by_guest(self) -> None:
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(self.mutation, variables=self.variables)
        content = response.json()
        self.assertIn(PERMISSION_DENIED_MESSAGE, content["errors"][0]["message"])


class TestCommunicationVisibility(HelixGraphQLTestCase):
    """Every read surface of a communication: guests see none of them, other roles see all."""

    def setUp(self) -> None:
        self.country = CountryFactory.create()
        self.contact = ContactFactory.create()
        self.communication = CommunicationFactory.create(contact=self.contact, country=self.country)
        self.query_string = """
        query CommunicationSurfaces($id: ID!, $contactId: ID!, $countryId: ID!) {
          communication(id: $id) {
            id
          }
          communicationList {
            totalCount
          }
          contact(id: $contactId) {
            communications {
              totalCount
            }
          }
          country(id: $countryId) {
            communications {
              id
            }
          }
        }
        """
        self.variables = {
            "id": str(self.communication.id),
            "contactId": str(self.contact.id),
            "countryId": str(self.country.id),
        }

    def test_guest_sees_no_communication_on_any_surface(self) -> None:
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(self.query_string, variables=self.variables)
        content = response.json()
        self.assertResponseNoErrors(response)
        data = content["data"]
        self.assertIsNone(data["communication"], content)
        self.assertEqual(data["communicationList"]["totalCount"], 0, content)
        self.assertEqual(data["contact"]["communications"]["totalCount"], 0, content)
        self.assertEqual(data["country"]["communications"], [], content)

    def test_monitoring_expert_sees_communication_on_every_surface(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(self.query_string, variables=self.variables)
        content = response.json()
        self.assertResponseNoErrors(response)
        data = content["data"]
        self.assertEqual(data["communication"]["id"], str(self.communication.id), content)
        self.assertEqual(data["communicationList"]["totalCount"], 1, content)
        self.assertEqual(data["contact"]["communications"]["totalCount"], 1, content)
        self.assertEqual([each["id"] for each in data["country"]["communications"]], [str(self.communication.id)], content)
