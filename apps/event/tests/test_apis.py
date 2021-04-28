from datetime import datetime, timedelta
import json

from apps.crisis.models import Crisis
from apps.users.enums import USER_ROLE
from apps.review.models import Review
from utils.factories import (
    CountryFactory,
    DisasterSubTypeFactory,
    CrisisFactory,
    ViolenceSubTypeFactory,
    EventFactory,
    EntryFactory,
)
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestCreateEventHelixGraphQLTestCase(HelixGraphQLTestCase):
    def setUp(self) -> None:
        countries = CountryFactory.create_batch(2)
        self.crisis = crisis = CrisisFactory.create()
        crisis.crisis_type = Crisis.CRISIS_TYPE.DISASTER
        crisis.save()
        crisis.countries.set(countries)
        self.mutation = '''mutation CreateEvent($input: EventCreateInputType!) {
            createEvent(data: $input) {
                errors
                result {
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
                    otherSubType
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
                }
                ok
                }
            }'''
        self.input = {
            "crisis": str(crisis.id),
            "name": "Event1",
            "eventType": "DISASTER",
            "glideNumber": "glide number",
            "disasterSubType": DisasterSubTypeFactory().id,
            "countries": [each.id for each in countries]
        }
        editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
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
        self.assertEqual(content['data']['createEvent']['result']['name'],
                         self.input['name'])

    def test_valid_event_creation_with_other_sub_type(self) -> None:
        self.input['eventType'] = "DISASTER"
        self.input['otherSubType'] = "DEVELOPMENT"  # this will not be set
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createEvent']['ok'], content)
        self.assertIsNone(content['data']['createEvent']['errors'], content)
        self.assertEqual(content['data']['createEvent']['result']['name'],
                         self.input['name'])
        self.assertEqual(content['data']['createEvent']['result']['otherSubType'],
                         None)

        self.crisis.crisis_type = Crisis.CRISIS_TYPE.OTHER
        self.crisis.save()

        self.input['eventType'] = "OTHER"
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createEvent']['ok'], content)
        self.assertIsNone(content['data']['createEvent']['errors'], content)
        self.assertEqual(content['data']['createEvent']['result']['name'],
                         self.input['name'])
        self.assertNotEqual(content['data']['createEvent']['result']['otherSubType'],
                            None)

    def test_invalid_filter_figure_countries_beyond_crisis(self) -> None:
        self.input['countries'] = [each.id for each in CountryFactory.create_batch(2)]
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['createEvent']['ok'], content)
        self.assertIn('countries', [item['field'] for item in content['data']['createEvent']['errors']], content)


class TestUpdateEvent(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.mutation = '''mutation UpdateEvent($input: EventUpdateInputType!) {
            updateEvent(data: $input) {
                errors
                result {
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
                }
                ok
                }
            }'''
        self.event = EventFactory.create(crisis=None)
        self.input = {
            "id": self.event.id,
            "endDate": "2020-10-29",
            "eventNarrative": "",
            "eventType": "CONFLICT",
            "name": "xyz",
            "startDate": "2020-10-20",
            "violenceSubType": ViolenceSubTypeFactory.create().id,
        }
        editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        self.force_login(editor)

    def test_invalid_event_dates_beyond_crisis(self):
        crisis = CrisisFactory.create()
        self.event.crisis = crisis
        self.event.save()

        crisis.start_date = datetime.today()
        crisis.end_date = datetime.today() + timedelta(days=10)
        crisis.save()
        self.input['startDate'] = (crisis.start_date - timedelta(days=1)).strftime('%Y-%m-%d')
        self.input['endDate'] = (crisis.end_date + timedelta(days=1)).strftime('%Y-%m-%d')
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['updateEvent']['ok'], content)
        self.assertIn('startDate', [item['field'] for item in content['data']['updateEvent']['errors']], content)
        self.assertIn('endDate', [item['field'] for item in content['data']['updateEvent']['errors']], content)

    def test_valid_event_update(self) -> None:
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateEvent']['ok'], content)
        self.assertIsNone(content['data']['updateEvent']['errors'], content)
        self.assertEqual(content['data']['updateEvent']['result']['name'],
                         self.input['name'])

    def test_invalid_update_event_by_guest(self):
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestDeleteEvent(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.mutation = '''mutation DeleteEvent($id: ID!) {
            deleteEvent(id: $id) {
                errors
                result {
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
                }
                ok
                }
            }'''
        self.event = EventFactory.create()
        self.variables = {
            "id": self.event.id,
        }
        editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
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
        self.assertEqual(content['data']['deleteEvent']['result']['name'],
                         self.event.name)
        self.assertEqual(int(content['data']['deleteEvent']['result']['id']),
                         self.event.id)

    def test_invalid_delete_event_by_guest(self):
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestEventListQuery(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.event1_name = 'blaone'
        self.q = '''
            query EventList($crisisByIds: [ID!], $name: String){
              eventList(crisisByIds: $crisisByIds, name: $name) {
                results {
                  id
                  reviewCount {
                    reviewCompleteCount
                    signedOffCount
                    toBeReviewedCount
                    underReviewCount
                  }
                }
              }
            }
        '''
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)

    def test_event_list_filter(self):
        event1 = EventFactory.create(name=self.event1_name)
        EventFactory.create(name='blatwo')
        variables = {
            "crisisByIds": [str(event1.crisis.id)]
        }
        response = self.query(self.q,
                              variables=variables)
        content = response.json()

        expected = [self.event1.id]
        self.assertResponseNoErrors(response)
        self.assertEqual([int(each['id']) for each in content['data']['eventList']['results']],
                         expected)

        variables = {
            "name": self.event1_name
        }
        response = self.query(self.q,
                              variables=variables)
        content = response.json()

        expected = [self.event1.id]
        self.assertResponseNoErrors(response)
        self.assertEqual(
            [int(each['id']) for each in content['data']['eventList']['results']],
            expected
        )

    def test_event_review_count_with_dataloader(self):
        event = EventFactory.create()
        r1 = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT_EDITOR.name,
        )
        r2 = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT_EDITOR.name,
        )
        entry = EntryFactory.create(
            event=event,
        )
        entry.reviewers.set([r1, r2])

        response = self.query(
            self.q,
        )
        content = response.json()
        # check the counts
        data = content['data']
        self.assertEqual(
            data['eventList']['results'][0]['reviewCount']['toBeReviewedCount'],
            2
        )
        self.assertEqual(
            data['eventList']['results'][0]['reviewCount']['underReviewCount'],
            None
        )

        # one reviewer starts reviewing
        Review.objects.create(
            entry=entry,
            created_by=r1,
            field='field',
            value=0,
        )
        response = self.query(
            self.q,
        )
        content = response.json()
        # check the counts
        data = content['data']
        self.assertEqual(
            data['eventList']['results'][0]['reviewCount']['toBeReviewedCount'],
            1
        )
        self.assertEqual(
            data['eventList']['results'][0]['reviewCount']['underReviewCount'],
            1
        )
        self.assertEqual(
            data['eventList']['results'][0]['reviewCount']['signedOffCount'],
            None
        )
        self.assertEqual(
            data['eventList']['results'][0]['reviewCount']['reviewCompleteCount'],
            None
        )
