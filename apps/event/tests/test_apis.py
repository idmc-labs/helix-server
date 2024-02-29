from datetime import datetime, timedelta
import json
from uuid import uuid4

from apps.crisis.models import Crisis
from apps.users.enums import USER_ROLE
from apps.entry.models import Figure
from apps.event.models import EventCode
from apps.report.models import Report
from apps.review.models import UnifiedReviewComment

from utils.factories import (
    CountryFactory,
    DisasterSubTypeFactory,
    CrisisFactory,
    ViolenceSubTypeFactory,
    EventFactory,
    EntryFactory,
    FigureFactory,
    OtherSubtypeFactory,
    OSMNameFactory,
    EventCodeFactory,
    ReportFactory,
    UnifiedReviewCommentFactory,
)
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, create_user_with_role
from apps.common.enums import QA_RULE_TYPE
from apps.contrib.migrate_commands import merge_events

from apps.contrib.models import BulkApiOperation


class TestDataMigrationTestCase(HelixGraphQLTestCase):
    def setUp(self):
        country1 = CountryFactory.create()
        self.event1, self.event2, self.event3 = EventFactory.create_batch(
            3,
            event_type=Crisis.CRISIS_TYPE.CONFLICT,
            countries=[country1],
        )
        entry1 = EntryFactory.create()
        figure_kwargs = {
            'entry': entry1,
            'country': country1,
            'category': Figure.FIGURE_CATEGORY_TYPES.IDPS.value,
        }
        FigureFactory.create_batch(10, event=self.event1, **figure_kwargs)
        FigureFactory.create_batch(15, event=self.event2, **figure_kwargs)

        for report in ReportFactory.create_batch(3):
            report.filter_figure_events.set([self.event1, self.event2])

        UnifiedReviewCommentFactory.create_batch(3, event=self.event2)

        # to arise validation error : Choose your start date after event start date
        FigureFactory.create(
            event=self.event3,
            start_date=self.event2.start_date - timedelta(days=2),
            **figure_kwargs
        )

    def test_event_merge(self):
        data = {
            self.event1.id: [self.event2.id, self.event3.id]
        }

        def _assert_bulk_operation_count(count):
            assert BulkApiOperation.objects.count() == count

        _assert_bulk_operation_count(0)
        merge_events(data)
        _assert_bulk_operation_count(1)

        self.assertEqual(Figure.objects.filter(event_id=self.event2.id).count(), 0)
        self.assertEqual(
            set(Figure.objects.exclude(event_id=self.event3.id).values_list('event_id', flat=True)),
            {self.event1.id}
        )

        # check for failed figure update
        self.assertNotEqual(
            BulkApiOperation.objects.first().failure_list,
            []
        )
        self.assertEqual(Figure.objects.filter(event_id=self.event3.id).count(), 1)

        # test report_filter_figure_events
        report_filter_figure_events_ids = []
        for report in Report.objects.all():
            report_filter_figure_events_ids.extend(
                list(report.filter_figure_events.all().values_list('id', flat=True))
            )
        self.assertEqual(
            set(report_filter_figure_events_ids),
            {self.event1.id}
        )
        self.assertEqual(Report.objects.filter(filter_figure_events=self.event2).count(), 0)

        # test event unified review comment.
        self.assertEqual(
            set(UnifiedReviewComment.objects.values_list('event_id', flat=True)),
            {self.event1.id}
        )
        self.assertEqual(UnifiedReviewComment.objects.filter(event=self.event2).count(), 0)


class TestCreateEventHelixGraphQLTestCase(HelixGraphQLTestCase):
    def setUp(self) -> None:
        countries = CountryFactory.create_batch(2)
        country1 = CountryFactory.create()
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
                    otherSubType {
                        id
                        name
                    }
                    violence {
                        name
                    }
                    violenceSubType {
                        name
                    }
                    eventCodes {
                        uuid
                        eventCode
                        eventCodeType
                        id
                        country {
                          id
                        }
                    }
                }
                ok
                }
            }'''
        self.input = {
            "crisis": str(crisis.id),
            "name": "Event1",
            "eventType": "DISASTER",
            "disasterSubType": DisasterSubTypeFactory().id,
            "countries": [each.id for each in countries],
            "startDate": "2014-01-01",
            "endDate": "2016-01-01",
            "eventNarrative": "event narrative",
            "otherSubType": OtherSubtypeFactory().id,
            "eventCodes": [
                {
                    "uuid": str(uuid4()),
                    "country": country1.id,
                    "eventCodeType": "GOV_ASSIGNED_IDENTIFIER",
                    "eventCode": "NEP-2021-YYY"
                },
                {
                    "uuid": str(uuid4()),
                    "country": country1.id,
                    "eventCodeType": "GLIDE_NUMBER",
                    "eventCode": "NEP-2021-XXX"
                },
                {
                    "uuid": str(uuid4()),
                    "country": country1.id,
                    "eventCodeType": "IFRC_APPEAL_ID",
                    "eventCode": "NEP-2021-ZZZ"
                },
            ]
        }
        editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
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
        self.assertIsNotNone(content['data']['createEvent']['result']['eventCodes'], content)
        self.assertEqual(content['data']['createEvent']['result']['eventCodes'][0]['eventCode'], 'NEP-2021-XXX')

    def test_valid_event_creation_with_other_sub_type(self) -> None:
        self.input['eventType'] = "DISASTER"
        self.input['otherSubType'] = OtherSubtypeFactory.create().id
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
        country1 = CountryFactory.create()
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
                    violenceSubType {
                        name
                    }
                    eventCodes {
                        eventCode
                        eventCodeType
                        uuid
                        id
                        country {
                          id
                        }
                    }
                }
                ok
                }
            }'''
        self.event = EventFactory.create(
            crisis=None,
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
        self.event_code1 = EventCodeFactory.create(
            event=self.event,
            country=country1,
            event_code_type=EventCode.EVENT_CODE_TYPE.GLIDE_NUMBER,
            event_code='Code-1'
        )
        EventCodeFactory.create(
            event=self.event,
            country=country1,
            event_code_type=EventCode.EVENT_CODE_TYPE.GOV_ASSIGNED_IDENTIFIER,
            event_code='Code-1'
        )
        EventCodeFactory.create(
            event=self.event,
            country=country1,
            event_code_type=EventCode.EVENT_CODE_TYPE.ACLED_ID,
            event_code='Code-1'
        )
        v_sub_type = ViolenceSubTypeFactory.create()
        self.input = {
            "id": self.event.id,
            "endDate": "2020-10-29",
            "eventNarrative": "event narrative",
            "eventType": "CONFLICT",
            "name": "xyz",
            "startDate": "2020-10-20",
            "violenceSubType": v_sub_type.id,
            "eventCodes": [
                {
                    "id": self.event_code1.id,
                    "uuid": str(uuid4()),
                    "country": country1.id,
                    "eventCodeType": "GOV_ASSIGNED_IDENTIFIER",
                    "eventCode": "NEP-2021-AAA"
                },
                {
                    "country": country1.id,
                    "uuid": str(uuid4()),
                    "eventCodeType": "IFRC_APPEAL_ID",
                    "eventCode": "NEP-2021-CCC"
                },
            ]
        }
        editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(editor)

    def test_invalid_event_dates_beyond_crisis(self):
        crisis = CrisisFactory.create()
        self.event.crisis = crisis
        self.event.save()

        crisis.start_date = datetime.today()
        crisis.end_date = datetime.today() + timedelta(days=10)
        crisis.save()
        self.input['crisis'] = crisis.id
        self.input['startDate'] = (crisis.start_date - timedelta(days=1)).strftime('%Y-%m-%d')
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['updateEvent']['ok'], content)
        self.assertIn('startDate', [item['field'] for item in content['data']['updateEvent']['errors']], content)

    def test_valid_event_update(self) -> None:
        country1 = CountryFactory.create()
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
        self.assertEqual(len(content['data']['updateEvent']['result']['eventCodes']), 2)
        self.assertEqual(
            EventCode.objects.get(id=self.event_code1.id).event_code_type,
            EventCode.EVENT_CODE_TYPE.GOV_ASSIGNED_IDENTIFIER.value
        )

        self.input["eventCodes"] = [
            {
                "id": content['data']['updateEvent']['result']['eventCodes'][0]['id'],
                "uuid": content['data']['updateEvent']['result']['eventCodes'][0]['uuid'],
                "country": country1.id,
                "eventCodeType": "GOV_ASSIGNED_IDENTIFIER",
                "eventCode": "NEP-2021-AAA"
            },
            {
                "id": content['data']['updateEvent']['result']['eventCodes'][1]['id'],
                "uuid": content['data']['updateEvent']['result']['eventCodes'][1]['uuid'],
                "country": country1.id,
                "eventCodeType": "IFRC_APPEAL_ID",
                "eventCode": "NEP-2021-CCC"
            },
        ]

        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateEvent']['ok'], content)
        self.assertIsNone(content['data']['updateEvent']['errors'], content)

        self.input["eventCodes"] = []

        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content1 = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content1['data']['updateEvent']['ok'], content1)
        self.assertIsNone(content1['data']['updateEvent']['errors'], content1)
        self.assertIsNone(content1['data']['updateEvent']['result']['eventCodes'], content1)

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
                    violenceSubType {
                        name
                    }
                }
                ok
                }
            }'''
        self.event = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
        self.variables = {
            "id": self.event.id,
        }
        editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
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
        self.q = '''
            query EventList($crisisByIds: [ID!], $name: String, $qaRule: String){
              eventList(filters: {crisisByIds: $crisisByIds, name: $name, qaRule: $qaRule}) {
                results {
                  id
                }
                totalCount
              }
            }
        '''
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)

    def test_event_list_filter(self):

        event1 = EventFactory.create(
            name='random event2',
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
        EventFactory.create(
            name='blatwo',
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
        variables = {
            "crisisByIds": [str(event1.crisis.id)]
        }
        response = self.query(self.q,
                              variables=variables)
        content = response.json()

        expected = [event1.id]
        self.assertResponseNoErrors(response)
        self.assertEqual([int(each['id']) for each in content['data']['eventList']['results']],
                         expected)

        variables = {
            "name": 'random event2'
        }
        response = self.query(self.q,
                              variables=variables)
        content = response.json()

        expected = [event1.id]
        self.assertResponseNoErrors(response)
        self.assertEqual(
            [int(each['id']) for each in content['data']['eventList']['results']],
            expected
        )

    def test_event_has_mutiple_recommended_figures(self):
        # Create event without entries and figures
        event1 = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )

        geo_location = OSMNameFactory.create(
            name='random location'
        )
        for i in range(3):
            entry1 = EntryFactory.create()
            FigureFactory.create(
                entry=entry1,
                role=Figure.ROLE.RECOMMENDED,
                category=Figure.FIGURE_CATEGORY_TYPES.IDPS.value,
                event=event1,
                geo_locations=[geo_location],
            )
            FigureFactory.create(
                entry=entry1,
                role=Figure.ROLE.RECOMMENDED,
                category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value,
                event=event1,
                geo_locations=[geo_location],
            )

        for i in range(3):
            entry1 = EntryFactory.create()
            FigureFactory.create(
                entry=entry1,
                role=Figure.ROLE.TRIANGULATION,
                category=Figure.FIGURE_CATEGORY_TYPES.IDPS.value,
                event=event1,
                geo_locations=[geo_location],
            )
            FigureFactory.create(
                entry=entry1,
                role=Figure.ROLE.TRIANGULATION,
                category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value,
                event=event1,
                geo_locations=[geo_location],
            )

        # Test event has no figures
        variables = {
            "qaRule": QA_RULE_TYPE.HAS_NO_RECOMMENDED_FIGURES.name
        }
        response = self.query(self.q, variables=variables)
        content = response.json()
        self.assertEqual(content['data']['eventList']['totalCount'], 0)

        # Test event with mutiple figures
        variables = {
            "qaRule": QA_RULE_TYPE.HAS_MULTIPLE_RECOMMENDED_FIGURES.name
        }
        response = self.query(self.q, variables=variables)
        content = response.json()
        self.assertEqual(content['data']['eventList']['totalCount'], 1)

    def test_should_ignore_events_form_qa_if_ignore_qs_flag_is_true(self):
        event = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
        # Create events with ignore_qa true
        geo_location = OSMNameFactory.create(
            name='random location2'
        )
        for i in range(3):
            entry1 = EntryFactory.create()
            FigureFactory.create(
                entry=entry1,
                role=Figure.ROLE.RECOMMENDED,
                category=Figure.FIGURE_CATEGORY_TYPES.IDPS.value,
                event=event,
                geo_locations=[geo_location],
            )
            FigureFactory.create(
                entry=entry1,
                role=Figure.ROLE.RECOMMENDED,
                category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value,
                event=event,
                geo_locations=[geo_location],
            )

        variables = {
            "qaRule": QA_RULE_TYPE.HAS_NO_RECOMMENDED_FIGURES.name
        }
        response = self.query(self.q, variables=variables)
        content = response.json()
        self.assertEqual(content['data']['eventList']['totalCount'], 0)

        variables = {
            "qaRule": QA_RULE_TYPE.HAS_MULTIPLE_RECOMMENDED_FIGURES.name
        }
        response = self.query(self.q, variables=variables)
        content = response.json()
        self.assertEqual(content['data']['eventList']['totalCount'], 1)


class CloneEventTest(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.mutation = '''mutation cloneEvent($event: ID!) {
            cloneEvent(data: {event: $event}) {
                errors
                result {
                    id
                    startDate
                    endDate
                    name
                    eventType
                    crisis {
                        id
                    }
                    violence {
                        id
                    }
                    violenceSubType {
                        id
                    }
                    actor {
                        id
                    }
                    disasterCategory {
                        id
                    }
                    disasterType {
                        id
                    }
                    countries {
                        id
                    }
                }
                ok
                errors
                }
            }'''
        self.event = EventFactory.create(
            name='test event',
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
        self.country = CountryFactory.create()
        self.event.countries.add(self.country)
        self.variables = {
            "event": self.event.id,
        }
        editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(editor)

    def test_event_list_filter(self):
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = response.json()
        cloned_event = content["data"]["cloneEvent"]["result"]
        # Check data cloned properly
        self.assertEqual(cloned_event["id"], str(self.event.id + 1))
        self.assertEqual(cloned_event["startDate"], str(self.event.start_date))
        self.assertEqual(cloned_event["endDate"], str(self.event.end_date))
        self.assertEqual(cloned_event["name"], f"Clone: {self.event.name}")
        # Check data cloned properly in foreign key fields
        self.assertEqual(cloned_event["crisis"]["id"], str(self.event.crisis.id))
        self.assertEqual(cloned_event["violence"]["id"], str(self.event.violence.id))
        self.assertEqual(cloned_event["violenceSubType"]["id"], str(self.event.violence_sub_type.id))
        self.assertEqual(cloned_event["actor"]["id"], str(self.event.actor.id))
        self.assertEqual(cloned_event["disasterCategory"]["id"], str(self.event.disaster_category.id))
        self.assertEqual(cloned_event["disasterType"]["id"], str(self.event.disaster_type.id))
        # Check data cloned properly in m2m key field
        self.assertEqual(cloned_event["countries"][0]["id"], str(self.country.id))
