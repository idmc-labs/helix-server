import json

from apps.users.roles import MONITORING_EXPERT_REVIEWER
from apps.resource.models import ResourceGroup
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestCreateResourceGroup(HelixGraphQLTestCase):
    def setUp(self):
        self.mutation = '''
            mutation CreateResourceGroup($input: ResourceGroupCreateInputType!) {
              createResourceGroup(resourceGroup: $input) {
                ok
                resourceGroup { 
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
        self.assertEqual(content['data']['createResourceGroup']['resourceGroup']['name'], self.input['name'])
        self.assertEqual(old + 1, ResourceGroup.objects.count())
