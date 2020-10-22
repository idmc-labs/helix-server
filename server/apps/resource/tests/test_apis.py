import json

from apps.users.roles import MONITORING_EXPERT_REVIEWER
from apps.resource.models import ResourceGroup
from utils.tests import HelixGraphQLTestCase, create_user_with_role
from utils.factories import CountryFactory, ResourceGroupFactory


class TestQueryResourceGroup(HelixGraphQLTestCase):
    def setUp(self):
        self.list_resource_groups = '''
            query MyQuery {
              resourceGroupList {
                results {
                  id
                }
              }
            }
        '''

    def test_unauthenticated_user_list_resource_groups(self):
        response = self.query(
            self.list_resource_groups
        )
        self.assertResponseNoErrors(response)


class TestCreateResourceGroup(HelixGraphQLTestCase):
    def setUp(self):
        self.mutation = '''
            mutation CreateResourceGroup($input: ResourceGroupCreateInputType!) {
              createResourceGroup(data: $input) {
                ok
                result {
                  name
                }
              }
            }
        '''
        self.input = {'name': 'group'}

    def test_valid_create_resource_group(self):
        old = ResourceGroup.objects.count()
        reviewer = create_user_with_role(MONITORING_EXPERT_REVIEWER)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createResourceGroup']['ok'], content)
        self.assertEqual(content['data']['createResourceGroup']['result']['name'], self.input['name'])
        self.assertEqual(old + 1, ResourceGroup.objects.count())


class TestCreateResource(HelixGraphQLTestCase):
    def setUp(self):
        self.reviewer = create_user_with_role(MONITORING_EXPERT_REVIEWER)
        self.group = ResourceGroupFactory.create(created_by=self.reviewer)
        self.countries = CountryFactory.create_batch(3)
        self.mutation = '''
            mutation CreateResource($input: ResourceCreateInputType!) {
              createResource(data: $input) {
                ok
                result {
                  name
                }
                errors {
                  field
                  messages
                }
              }
            }
        '''
        self.input = {'name': 'name',
                      'url': 'http://example.com',
                      'group': self.group.id,
                      'countries': [each.id for each in self.countries]}
        self.force_login(self.reviewer)

    def test_valid_create_resource(self):
        self.force_login(self.reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createResource']['ok'], content)
        self.assertEqual(content['data']['createResource']['result']['name'], self.input['name'])

    def test_invalid_create_without_countries(self):
        self.input['countries'] = []

        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['createResource']['ok'], content)
        self.assertIn('countries', [each['field'] for each in content['data']['createResource']['errors']], content)

    def test_invalid_create_different_users_resource_group(self):
        reviewer2 = create_user_with_role(MONITORING_EXPERT_REVIEWER)
        self.force_login(reviewer2)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['createResource']['ok'], content)
        self.assertIn('group', [each['field'] for each in content['data']['createResource']['errors']])
