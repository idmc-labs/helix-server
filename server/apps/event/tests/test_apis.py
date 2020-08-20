import json

from utils.factories import CountryFactory, DisasterCategoryFactory, CrisisFactory
from utils.tests import HelixGraphQLTestCase


class TestCreateEvent(HelixGraphQLTestCase):
    def setUp(self) -> None:
        countries = CountryFactory.create_batch(2)
        self.mutation = f'''mutation CreateEvent($input: EventCreateInputType!) {{
            createEvent(event: $input) {{
                errors {{
                    field
                    messages
                }}
                event {{
                    disasterType {{
                        name
                    }}
                    disasterCategory {{
                        name
                    }}
                    disasterSubCategory {{
                        name
                    }}
                    disasterSubType {{
                        name
                    }}
                    startDate
                    endDate
                    name
                    eventType
                    violence {{
                        name
                    }}
                    triggerSubType {{
                        name
                    }}
                    trigger {{
                        name
                    }}
                    violenceSubType {{
                        name
                    }}
                    countries {{
                        name
                    }}
                }}
                ok
                }}
            }}'''
        self.input = {
            "crisis": CrisisFactory().id,
            "name": "Event1",
            "eventType": "DISASTER",
            "glideNumber": "glide number",
            "disasterCategory": DisasterCategoryFactory().id,
            "countries": [each.id for each in countries]
        }

    def test_valid_event_creation(self) -> None:
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createEvent']['ok'], content)
        self.assertIsNone(content['data']['createEvent']['errors'], content)
        self.assertEqual(content['data']['createEvent']['event']['name'],
                         self.input['name'])
        self.assertEqual(len(content['data']['createEvent']['event']['countries']),
                         len(self.input['countries']))

    def test_invalid_disaster_event_without_glide(self) -> None:
        self.input.pop('glideNumber')
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['createEvent']['ok'], content)
        self.assertIn('glide_number', [each['field'] for each in content['data']['createEvent']['errors']])

    def test_invalid_conflict_event_without_violence(self) -> None:
        self.input.update({
            "eventType": "CONFLICT"
        })
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['createEvent']['ok'], content)
        self.assertIn('violence', [each['field'] for each in content['data']['createEvent']['errors']])
