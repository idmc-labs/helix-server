import json

from apps.users.roles import MONITORING_EXPERT_REVIEWER, GUEST
from utils.factories import OrganizationFactory, OrganizationKindFactory
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestCreateOrganization(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.mutation = '''
        mutation CreateOrganization($input: OrganizationCreateInputType!) {
            createOrganization(organization: $input) {
                ok
                errors {
                    field
                    messages
                }
                organization {
                    id
                    methodology
                    title
                    shortName
                    sourceDetailMethodology
                }
            }
        }
        '''
        self.input = {
            "title": "Title1",
            "shortName": "ABC",
            "methodology": "Methodology1",
            "sourceDetailMethodology": "Source1"
        }

    def test_valid_organization_creation(self) -> None:
        reviewer = create_user_with_role(MONITORING_EXPERT_REVIEWER)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createOrganization']['ok'], content)
        self.assertEqual(content['data']['createOrganization']['organization']['title'],
                         self.input['title'])
        self.assertEqual(content['data']['createOrganization']['organization']['shortName'],
                         self.input['shortName'])

    def test_invalid_organization_creation_by_guest(self) -> None:
        guest = create_user_with_role(GUEST)
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
            updateOrganization(organization: $input) {
                ok
                errors {
                    field
                    messages
                }
                organization {
                    id
                    methodology
                    title
                    shortName
                    sourceDetailMethodology
                }
            }
        }
        '''
        self.input = {
            "id": str(self.organization.id),
            "methodology": "New1"
        }

    def test_valid_organization_update(self) -> None:
        reviewer = create_user_with_role(MONITORING_EXPERT_REVIEWER)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateOrganization']['ok'], content)
        self.assertEqual(content['data']['updateOrganization']['organization']['id'],
                         self.input['id'])
        self.assertEqual(content['data']['updateOrganization']['organization']['methodology'],
                         self.input['methodology'])

    def test_invalid_organization_update_by_guest(self) -> None:
        guest = create_user_with_role(GUEST)
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
                errors {
                    field
                    messages
                }
                organization {
                    id
                }
            }
        }
        '''
        self.variables = {
            "id": str(self.organization.id),
        }

    def test_valid_organization_delete(self) -> None:
        reviewer = create_user_with_role(MONITORING_EXPERT_REVIEWER)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            variables=self.variables
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['deleteOrganization']['ok'], content)
        self.assertEqual(content['data']['deleteOrganization']['organization']['id'], self.variables['id'])

    def test_invalid_organization_delete_by_guest(self) -> None:
        guest = create_user_with_role(GUEST)
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
            createOrganizationKind(organizationKind: $input) {
                ok
                errors {
                    field
                    messages
                }
                organizationKind {
                    id
                    title
                }
            }
        }
        '''
        self.input = {
            "title": "Title1",
        }

    def test_valid_organization_kind_creation(self) -> None:
        reviewer = create_user_with_role(MONITORING_EXPERT_REVIEWER)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createOrganizationKind']['ok'], content)
        self.assertIsNotNone(content['data']['createOrganizationKind']['organizationKind']['id'])
        self.assertEqual(content['data']['createOrganizationKind']['organizationKind']['title'],
                         self.input['title'])

    def test_invalid_organization_kind_creation_by_guest(self) -> None:
        guest = create_user_with_role(GUEST)
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
            updateOrganizationKind(organizationKind: $input) {
                ok
                errors {
                    field
                    messages
                }
                organizationKind {
                    id
                    title
                }
            }
        }
        '''
        self.input = {
            "id": str(self.organization_kind.id),
            "title": "New1"
        }

    def test_valid_organization_kind_update(self) -> None:
        reviewer = create_user_with_role(MONITORING_EXPERT_REVIEWER)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateOrganizationKind']['ok'], content)
        self.assertEqual(content['data']['updateOrganizationKind']['organizationKind']['id'],
                         self.input['id'])
        self.assertEqual(content['data']['updateOrganizationKind']['organizationKind']['title'],
                         self.input['title'])

    def test_invalid_organization_kind_update_by_guest(self) -> None:
        guest = create_user_with_role(GUEST)
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
                errors {
                    field
                    messages
                }
                organizationKind {
                    id
                }
            }
        }
        '''
        self.variables = {
            "id": str(self.organization.id),
        }

    def test_valid_organization_kind_delete(self) -> None:
        reviewer = create_user_with_role(MONITORING_EXPERT_REVIEWER)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            variables=self.variables
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['deleteOrganizationKind']['ok'], content)
        self.assertEqual(content['data']['deleteOrganizationKind']['organizationKind']['id'],
                         self.variables['id'])

    def test_invalid_organization_kind_delete_by_guest(self) -> None:
        guest = create_user_with_role(GUEST)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            variables=self.variables
        )

        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])
