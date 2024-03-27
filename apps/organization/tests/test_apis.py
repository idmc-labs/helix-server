import json
from datetime import datetime
from unittest.mock import patch

from apps.users.enums import USER_ROLE
from utils.factories import OrganizationFactory, OrganizationKindFactory
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestCreateOrganization(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.mutation = '''
        mutation CreateOrganization($input: OrganizationCreateInputType!) {
            createOrganization(data: $input) {
                ok
                errors
                result {
                    id
                    methodology
                    name
                    shortName
                }
            }
        }
        '''
        self.input = {
            "name": "Title1",
            "shortName": "ABC",
            "methodology": "Methodology1",
        }

    def test_valid_organization_creation(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createOrganization']['ok'], content)
        self.assertEqual(content['data']['createOrganization']['result']['name'],
                         self.input['name'])
        self.assertEqual(content['data']['createOrganization']['result']['shortName'],
                         self.input['shortName'])

    def test_invalid_organization_creation_by_guest(self) -> None:
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestUpdateOrganization(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.organization = OrganizationFactory.create()
        self.mutation = '''
        mutation UpdateOrganization($input: OrganizationUpdateInputType!) {
            updateOrganization(data: $input) {
                ok
                errors
                result {
                    id
                    methodology
                    name
                    shortName
                }
            }
        }
        '''
        self.input = {
            "id": str(self.organization.id),
            "methodology": "New1"
        }

    def test_valid_organization_update(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateOrganization']['ok'], content)
        self.assertEqual(content['data']['updateOrganization']['result']['id'],
                         self.input['id'])
        self.assertEqual(content['data']['updateOrganization']['result']['methodology'],
                         self.input['methodology'])

    def test_invalid_organization_update_by_guest(self) -> None:
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestDeleteOrganization(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.organization = OrganizationFactory.create()
        self.mutation = '''
        mutation DeleteOrganization($id: ID!) {
            deleteOrganization(id: $id) {
                ok
                errors
                result {
                    id
                }
            }
        }
        '''
        self.variables = {
            "id": str(self.organization.id),
        }

    def test_valid_organization_delete(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            variables=self.variables
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['deleteOrganization']['ok'], content)
        self.assertEqual(content['data']['deleteOrganization']['result']['id'], self.variables['id'])

    def test_invalid_organization_delete_by_guest(self) -> None:
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            variables=self.variables
        )

        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestCreateOrganizationKind(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.mutation = '''
        mutation CreateOrganizationKind($input: OrganizationKindCreateInputType!) {
            createOrganizationKind(data: $input) {
                ok
                errors
                result {
                    id
                    name
                }
            }
        }
        '''
        self.input = {
            "name": "Title1",
        }

    def test_valid_organization_kind_creation(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])

    def test_invalid_organization_kind_creation_by_guest(self) -> None:
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestUpdateOrganizationKind(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.organization_kind = OrganizationKindFactory.create()
        self.mutation = '''
        mutation UpdateOrganizationKind($input: OrganizationKindUpdateInputType!) {
            updateOrganizationKind(data: $input) {
                ok
                errors
                result {
                    id
                    name
                }
            }
        }
        '''
        self.input = {
            "id": str(self.organization_kind.id),
            "name": "New1"
        }

    def test_valid_organization_kind_update(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])

    def test_invalid_organization_kind_update_by_guest(self) -> None:
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestDeleteOrganizationKind(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.organization = OrganizationKindFactory.create()
        self.mutation = '''
        mutation DeleteOrganizationKind($id: ID!) {
            deleteOrganizationKind(id: $id) {
                ok
                errors
                result {
                    id
                }
            }
        }
        '''
        self.variables = {
            "id": str(self.organization.id),
        }

    def test_valid_organization_kind_delete(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])

    def test_invalid_organization_kind_delete_by_guest(self) -> None:
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            variables=self.variables
        )

        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestQueryResourceGroup(HelixGraphQLTestCase):
    def setUp(self):
        self.list_organizations = '''
            query MyQuery($ordering: String) {
              organizationList(ordering: $ordering) {
                results {
                  id
                  shortName
                }
              }
            }
        '''
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)

    def test_organizations_ordering(self):
        with patch('django.utils.timezone.now', return_value=datetime(2020, 9, 9, 10, 6, 0)):
            org1 = OrganizationFactory.create(short_name='abc')
            org3 = OrganizationFactory.create(short_name='xyz')
        with patch('django.utils.timezone.now', return_value=datetime(2020, 10, 9, 10, 6, 0)):
            org2 = OrganizationFactory.create(short_name='abc')
        vars = {
            'ordering': "shortName,-createdAt"
        }
        expected = [org2.id, org1.id, org3.id]
        response = self.query(
            self.list_organizations,
            variables=vars
        )
        self.assertResponseNoErrors(response)
        content = response.json()
        obtained = [int(each['id']) for each in content['data']['organizationList']['results']]
        self.assertEqual(expected, obtained)

        vars = {
            'ordering': "-shortName,createdAt"
        }
        response = self.query(
            self.list_organizations,
            variables=vars
        )
        expected = [org3.id, org1.id, org2.id]
        content = response.json()
        obtained = [int(each['id']) for each in content['data']['organizationList']['results']]
        self.assertEqual(expected, obtained)
