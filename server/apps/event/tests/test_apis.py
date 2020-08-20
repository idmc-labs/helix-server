import json

from utils.factories import CountryFactory
from utils.tests import HelixGraphQLTestCase


class TestCreateCrisis(HelixGraphQLTestCase):
    def setUp(self) -> None:
        countries = CountryFactory.create_batch(2)
        self.mutation = f'''mutation MyMutation($input: CrisisCreateInputType!) {{
            createCrisis(crisis: $input) {{
                crisis {{
                    countries {{
                        totalCount
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
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        print(content)
        self.assertTrue(content['data']['createCrisis']['ok'], content)
        self.assertEqual(content['data']['createCrisis']['crisis']['name'], self.input['name'])
        self.assertEqual(content['data']['createCrisis']['crisis']['countries']['totalCount'],
                         len(self.input['countries']))
