import json

from apps.users.enums import USER_ROLE
from utils.factories import CountryFactory, ContactFactory, OrganizationFactory, CommunicationMediumFactory
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestCreateContact(HelixGraphQLTestCase):
    def setUp(self) -> None:
        countries = CountryFactory.create_batch(2)
        organization = OrganizationFactory.create()
        self.mutation = '''
        mutation CreateContact($input: ContactCreateInputType!) {
            createContact(data: $input) {
                ok
                errors {
                    field
                    messages
                }
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
        '''
        self.input = {
            "designation": "MR",
            "firstName": "first",
            "lastName": "last",
            "gender": "MALE",
            "jobTitle": "dev",
            "organization": str(organization.id),
            "countriesOfOperation": [each.id for each in countries]
        }

    def test_valid_contact_creation(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createContact']['ok'], content)
        self.assertEqual(content['data']['createContact']['result']['firstName'], self.input['firstName'])
        self.assertEqual(content['data']['createContact']['result']['organization']['id'],
                         self.input['organization'])
        self.assertEqual(len(content['data']['createContact']['result']['countriesOfOperation']),
                         len(self.input['countriesOfOperation']))

    def test_invalid_contact_creation_by_guest(self) -> None:
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestUpdateContact(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.contact = ContactFactory.create()
        self.mutation = '''
        mutation UpdateContact($input: ContactUpdateInputType!) {
            updateContact(data: $input) {
                ok
                errors {
                    field
                    messages
                }
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
        '''
        self.input = {
            "id": self.contact.id,
            "firstName": "new name",
        }

    def test_valid_contact_update(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateContact']['ok'], content)
        self.assertEqual(content['data']['updateContact']['result']['firstName'], self.input['firstName'])
        self.assertEqual(content['data']['updateContact']['result']['lastName'], self.contact.last_name)

    def test_invalid_contact_update_by_guest(self) -> None:
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestDeleteContact(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.contact = ContactFactory.create()
        self.mutation = '''
        mutation DeleteContact($id: ID!) {
            deleteContact(id: $id) {
                ok
                errors {
                    field
                    messages
                }
                result {
                    id
                }
            }
        }
        '''
        self.variables = {
            "id": str(self.contact.id),
        }

    def test_valid_contact_delete(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            variables=self.variables
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['deleteContact']['ok'], content)
        self.assertEqual(content['data']['deleteContact']['result']['id'], self.variables['id'])

    def test_invalid_contact_delete_by_guest(self) -> None:
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            variables=self.variables
        )

        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestCommunication(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.mutation = '''
        mutation MyMutation($input: CommunicationCreateInputType!) {
          createCommunication(data: $input) {
            ok
            errors {
              field
              messages
            }
            result {
              id
              medium {
                name
              }
            }
          }
        }
        '''
        self.contact = ContactFactory.create()
        self.medium = CommunicationMediumFactory.create()
        self.input = {"contact": str(self.contact.id), "subject": "Subject", "content": "Content", "medium": str(self.medium.id)}

    def test_valid_communication_creation(self):
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createCommunication']['ok'], content)

