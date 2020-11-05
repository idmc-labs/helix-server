import json

from apps.users.roles import MONITORING_EXPERT_REVIEWER, GUEST, MONITORING_EXPERT_EDITOR
from utils.factories import CountryFactory, CrisisFactory
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestCreateCrisis(HelixGraphQLTestCase):
    def setUp(self) -> None:
        countries = CountryFactory.create_batch(2)
        self.mutation = f'''mutation MyMutation($input: CrisisCreateInputType!) {{
            createCrisis(data: $input) {{
                result {{
                    countries {{
                        id
                    }}
                    name
                }}
                ok
                errors {{
                    field
                    messages
                }}
            }}
        }}'''
        self.input = {
            "name": "disss",
            "crisisType": "DISASTER",
            "countries": [each.id for each in countries],
            "crisisNarrative": "a naarrrative"
        }

    def test_valid_crisis_creation(self) -> None:
        reviewer = create_user_with_role(MONITORING_EXPERT_REVIEWER)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createCrisis']['ok'], content)
        self.assertEqual(content['data']['createCrisis']['result']['name'], self.input['name'])
        self.assertEqual(len(content['data']['createCrisis']['result']['countries']),
                         len(self.input['countries']))

    def test_invalid_crisis_creation_by_guest(self) -> None:
        guest = create_user_with_role(GUEST)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestCrisisUpdate(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(MONITORING_EXPERT_EDITOR)
        self.crisis = CrisisFactory.create(
            created_by=self.editor
        )
        self.mutation = """
            mutation UpdateCrisis($input: CrisisUpdateInputType!) {
              updateCrisis(data: $input) {
                ok
                errors {
                  field
                  messages
                }
                result {
                  name
                }
              }
            }
        """
        self.input = {
            "id": self.crisis.id,
            "name": "New Name"
        }

    def test_valid_update_crisis(self):
        self.force_login(self.editor)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateCrisis']['ok'], content)
        self.assertEqual(content['data']['updateCrisis']['result']['name'],
                         self.input['name'])

    def test_valid_update_crisis_by_different_user(self):
        reviewer = create_user_with_role(MONITORING_EXPERT_REVIEWER)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateCrisis']['ok'], content)
        self.assertEqual(content['data']['updateCrisis']['result']['name'],
                         self.input['name'])

    def test_invalid_update_crisis_by_guest(self):
        guest = create_user_with_role(GUEST)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestEntryDelete(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(MONITORING_EXPERT_EDITOR)
        self.crisis = CrisisFactory.create(
            created_by=self.editor
        )
        self.mutation = """
            mutation DeleteCrisis($id: ID!) {
              deleteCrisis(id: $id) {
                ok
                errors {
                  field
                  messages
                }
                result {
                  name
                }
              }
            }
        """
        self.variables = {
            "id": self.crisis.id,
        }

    def test_valid_delete_crisis(self):
        self.force_login(self.editor)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['deleteCrisis']['ok'], content)
        self.assertIsNotNone(content['data']['deleteCrisis']['result']['name'])

    def test_valid_delete_crisis_by_different_monitoring_expert(self):
        editor2 = create_user_with_role(MONITORING_EXPERT_EDITOR)
        self.force_login(editor2)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['deleteCrisis']['ok'], content)
        self.assertIsNotNone(content['data']['deleteCrisis']['result']['name'])

    def test_invalid_delete_crisis_by_guest(self):
        guest = create_user_with_role(GUEST)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])
