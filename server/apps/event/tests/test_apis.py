import json

from apps.users.roles import MONITORING_EXPERT_EDITOR, GUEST
from utils.factories import CountryFactory, DisasterCategoryFactory, CrisisFactory, ViolenceFactory, EventFactory
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestCreateEvent(HelixGraphQLTestCase):
    def setUp(self) -> None:
        countries = CountryFactory.create_batch(2)
        self.mutation = '''mutation CreateEvent($input: EventCreateInputType!) {
            createEvent(event: $input) {
                errors {
                    field
                    messages
                }
                event {
                    disasterType {
                        name
                    }
                    disasterCategory {
                        name
                    }
                    disasterSubCategory {
                        name
                    }
                    disasterSubType {
                        name
                    }
                    startDate
                    endDate
                    name
                    eventType
                    violence {
                        name
                    }
                    triggerSubType {
                        name
                    }
                    trigger {
                        name
                    }
                    violenceSubType {
                        name
                    }
                    countries {
                        name
                    }
                }
                ok
                }
            }'''
        self.input = {
            "crisis": CrisisFactory().id,
            "name": "Event1",
            "eventType": "DISASTER",
            "glideNumber": "glide number",
            "disasterCategory": DisasterCategoryFactory().id,
            "countries": [each.id for each in countries]
        }
        editor = create_user_with_role(MONITORING_EXPERT_EDITOR)
        self.force_login(editor)

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


class TestUpdateEvent(HelixGraphQLTestCase):
    def setUp(self) -> None:
        countries = CountryFactory.create_batch(2)
        self.mutation = '''mutation UpdateEvent($input: EventUpdateInputType!) {
            updateEvent(event: $input) {
                errors {
                    field
                    messages
                }
                event {
                    startDate
                    endDate
                    name
                    eventType
                    violence {
                        name
                    }
                    triggerSubType {
                        name
                    }
                    trigger {
                        name
                    }
                    violenceSubType {
                        name
                    }
                    countries {
                        name
                    }
                }
                ok
                }
            }'''
        self.input = {
            "id": EventFactory.create().id,
            "countries": [each.id for each in countries],
            "endDate": "2020-10-29",
            "eventNarrative": "",
            "eventType": "CONFLICT",
            "name": "xyz",
            "startDate": "2020-10-20",
            "violence": ViolenceFactory.create().id,
        }
        editor = create_user_with_role(MONITORING_EXPERT_EDITOR)
        self.force_login(editor)

    def test_valid_event_update(self) -> None:
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateEvent']['ok'], content)
        self.assertIsNone(content['data']['updateEvent']['errors'], content)
        self.assertEqual(content['data']['updateEvent']['event']['name'],
                         self.input['name'])
        self.assertEqual(len(content['data']['updateEvent']['event']['countries']),
                         len(self.input['countries']))

    def test_invalid_update_event_by_guest(self):
        guest = create_user_with_role(GUEST)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)
        self.assertIn('You do not have permission', content['errors'][0]['message'])


class TestDeleteEvent(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.mutation = '''mutation DeleteEvent($id: ID!) {
            deleteEvent(id: $id) {
                errors {
                    field
                    messages
                }
                event {
                    id
                    startDate
                    endDate
                    name
                    eventType
                    violence {
                        name
                    }
                    triggerSubType {
                        name
                    }
                    trigger {
                        name
                    }
                    violenceSubType {
                        name
                    }
                    countries {
                        name
                    }
                }
                ok
                }
            }'''
        self.event = EventFactory.create()
        self.variables = {
            "id": self.event.id,
        }
        editor = create_user_with_role(MONITORING_EXPERT_EDITOR)
        self.force_login(editor)

    def test_valid_event_delete(self) -> None:
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['deleteEvent']['ok'], content)
        self.assertIsNone(content['data']['deleteEvent']['errors'], content)
        self.assertEqual(content['data']['deleteEvent']['event']['name'],
                         self.event.name)
        self.assertEqual(int(content['data']['deleteEvent']['event']['id']),
                         self.event.id)

    def test_invalid_delete_event_by_guest(self):
        guest = create_user_with_role(GUEST)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = json.loads(response.content)
        self.assertIn('You do not have permission', content['errors'][0]['message'])
