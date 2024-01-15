from copy import deepcopy as copy
from uuid import uuid4
from unittest.mock import patch, call

from django.test import override_settings
from django.core.exceptions import PermissionDenied

from utils.tests import HelixGraphQLTestCase, create_user_with_role
from utils.factories import (
    EntryFactory,
    CountryFactory,
    EventFactory,
    FigureFactory,
)

from apps.crisis.models import Crisis
from apps.users.enums import USER_ROLE
from apps.event.models import Event
from apps.entry.models import Figure, OSMName
from apps.entry.mutations import BulkUpdateFigures
from apps.notification.models import Notification


def get_first_error_fields(errors):
    return [
        error['field']
        for obj_errors in errors
        if obj_errors is not None
        for error in obj_errors
    ]


@patch('apps.entry.mutations.BulkUpdateFigureManager.add_event')
@patch(
    'apps.entry.mutations.BulkUpdateFigureManager.__exit__',
    # Using side_effect to avoid suppressing exceptions
    side_effect=lambda *_: False,
)
class TestBulkFigureUpdate(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country_1 = CountryFactory.create(iso2='JP', iso3='JPN')
        self.country_2 = CountryFactory.create(iso2='AF', iso3='AFC')
        self.event = EventFactory.create(event_type=Crisis.CRISIS_TYPE.CONFLICT.value)
        self.event.countries.add(self.country_1, self.country_2)
        self.fig_cat = Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.entry = EntryFactory.create(article_title="test", publish_date="2020-02-02")

        self.f1, self.f2, self.f3 = FigureFactory.create_batch(3, event=self.event, entry=self.entry)

        self.geo_locaiton_1 = {
            'uuid': str(uuid4()),
            'rank': 101,
            'country': 'Japan',
            'countryCode': self.country_1.iso2,
            'osmId': 'xxxx',
            'osmType': 'yyyy',
            'displayName': 'xxxx',
            'lat': 44,
            'lon': 44,
            'name': 'Jp',
            'accuracy': OSMName.OSM_ACCURACY.ADM0.name,
            'identifier': OSMName.IDENTIFIER.ORIGIN.name,
        }
        self.geo_locaiton_2 = {
            'uuid': str(uuid4()),
            'rank': 10,
            'country': 'Africa',
            'countryCode': self.country_2.iso2,
            'osmId': 'hhh',
            'osmType': 'kkk',
            'displayName': 'jj',
            'lat': 55,
            'lon': 55,
            'name': 'AFC',
            'accuracy': OSMName.OSM_ACCURACY.ADM0.name,
            'identifier': OSMName.IDENTIFIER.ORIGIN.name,
        }
        self.figure_item_input = {
            "id": self.f3.id,
            "entry": self.entry.id,
            "uuid": str(uuid4()),
            "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
            "includeIdu": False,
            "event": self.event.id,
            "reported": 50,
            "figureCause": Crisis.CRISIS_TYPE.CONFLICT.name,
            "geoLocations": [self.geo_locaiton_1],
            "country": self.country_1.id,
        }

        self.figure_bulk_mutation = """
            mutation BulkUpdateFigures($items: [FigureUpdateInputType!], $delete_ids: [ID!]) {
                bulkUpdateFigures(items: $items, deleteIds: $delete_ids) {
                    errors
                    deletedResult {
                      id
                    }
                    result {
                      id
                      figureCause
                      includeIdu
                      unit
                      entry {
                        id
                        articleTitle
                      }
                      event {
                        id
                        name
                      }
                    }
                }
            }
        """
        self.force_login(self.editor)

    def test_can_bulk_create_and_delete_figures(
        self,
        mock_bulk_update_figure_manager_exit,
        mock_bulk_update_figure_manager_add_event,
    ):
        figures = [
            {
                "uuid": str(uuid4()),
                "country": self.country_1.id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 100,
                "unit": Figure.UNIT.PERSON.name,
                "term": Figure.FIGURE_TERMS.EVACUATED.name,
                "category": self.fig_cat.name,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2019-10-10",
                "includeIdu": True,
                "excerptIdu": "example xxx",
                "geoLocations": [self.geo_locaiton_1],
                'calculationLogic': 'test test logic',
                'sourceExcerpt': 'source test excerpt',
                'event': self.event.id,
                "figureCause": Crisis.CRISIS_TYPE.CONFLICT.name,
                "entry": self.entry.id,
            },
            {
                "uuid": str(uuid4()),
                "country": self.country_2.id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 300,
                "unit": Figure.UNIT.PERSON.name,
                "term": Figure.FIGURE_TERMS.EVACUATED.name,
                "category": self.fig_cat.name,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2020-10-10",
                "includeIdu": True,
                "excerptIdu": "excerpt for test",
                "geoLocations": [self.geo_locaiton_2],
                'calculationLogic': 'test check logics',
                'sourceExcerpt': 'source excerpt content',
                'event': self.event.id,
                "figureCause": Crisis.CRISIS_TYPE.CONFLICT.name,
                "entry": self.entry.id,
            },
            {
                "uuid": str(uuid4()),
                "country": self.country_1.id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 500,
                "unit": Figure.UNIT.PERSON.name,
                "term": Figure.FIGURE_TERMS.EVACUATED.name,
                "category": self.fig_cat.name,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2022-10-10",
                "includeIdu": True,
                "excerptIdu": "test excerpt ....",
                "geoLocations": [self.geo_locaiton_1],
                'calculationLogic': 'test logics ...',
                'sourceExcerpt': 'source excerpt ...',
                'event': self.event.id,
                "figureCause": Crisis.CRISIS_TYPE.CONFLICT.name,
                "entry": self.entry.id,
            },
        ]

        figure_ids = [self.f1.id, self.f2.id, self.f3.id]
        mock_bulk_update_figure_manager_add_event.assert_not_called()
        mock_bulk_update_figure_manager_exit.assert_not_called()
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": figures,
                "delete_ids": figure_ids,
            },
        )

        # Test created
        content_data = response.json()['data']['bulkUpdateFigures']
        self.assertResponseNoErrors(response)
        self.assertEqual(content_data['errors'], [None] * 3)
        self.assertEqual(len(content_data['result']), 3)
        self.assertNotIn(None, content_data['result'])
        self.assertEqual(len(content_data['deletedResult']), len(figure_ids), content_data)
        assert mock_bulk_update_figure_manager_add_event.call_count == 6
        mock_bulk_update_figure_manager_add_event.assert_has_calls([call(self.event.id)])
        mock_bulk_update_figure_manager_exit.assert_called_once()

        # Test bulk deleted
        self.assertEqual(Figure.objects.filter(id__in=figure_ids).count(), 0)

        # Check each item
        for created_figure in content_data['result']:
            self.assertEqual(created_figure['figureCause'], Crisis.CRISIS_TYPE.CONFLICT.name)
            self.assertEqual(created_figure['includeIdu'], True)
            self.assertEqual(created_figure['entry']['id'], str(self.entry.id))

    def test_can_bulk_update_and_delete_figures(
        self,
        mock_bulk_update_figure_manager_exit,
        mock_bulk_update_figure_manager_add_event,
    ):
        figures = [
            {
                "id": self.f1.id,
                "entry": self.entry.id,
                "uuid": str(uuid4()),
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "includeIdu": False,
                "event": self.event.id,
                "reported": 1000,
                "figureCause": Crisis.CRISIS_TYPE.CONFLICT.name,
                "geoLocations": [self.geo_locaiton_1],
                "country": self.country_1.id,
            },
            {
                "id": self.f2.id,
                "entry": self.entry.id,
                "uuid": str(uuid4()),
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "includeIdu": False,
                "event": self.event.id,
                "reported": 1000,
                "figureCause": Crisis.CRISIS_TYPE.CONFLICT.name,
                "geoLocations": [self.geo_locaiton_1],
                "country": self.country_1.id,
            },
        ]
        figure_ids = [self.f3.id]
        mock_bulk_update_figure_manager_add_event.assert_not_called()
        mock_bulk_update_figure_manager_exit.assert_not_called()
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": figures,
                "delete_ids": figure_ids,
            },
        )
        assert mock_bulk_update_figure_manager_add_event.call_count == 3
        mock_bulk_update_figure_manager_add_event.assert_has_calls([call(self.event.id)])
        mock_bulk_update_figure_manager_exit.assert_called_once()

        # Test bulk deleted
        self.assertEqual(Figure.objects.filter(id__in=figure_ids).count(), 0)

        # Test updated
        content_data = response.json()['data']['bulkUpdateFigures']
        self.assertResponseNoErrors(response)
        self.assertEqual(content_data['errors'], [None] * 2)
        self.assertEqual(len(content_data['result']), 2)
        self.assertNotIn(None, content_data['result'])
        assert None not in content_data['result']

        # Check each item
        for updated_figure in content_data['result']:
            self.assertEqual(updated_figure['figureCause'], Crisis.CRISIS_TYPE.CONFLICT.name)
            self.assertEqual(updated_figure['includeIdu'], False)
            self.assertEqual(updated_figure['entry']['id'], str(self.entry.id))

    def test_household_size_validation(
        self,
        mock_bulk_update_figure_manager_exit,
        mock_bulk_update_figure_manager_add_event,
    ):
        """
        reported <= disaggregationLocationCamp + disaggregationLocationNonCamp
        """
        figure_item_input = copy(self.figure_item_input)
        figure_item_input.update({
            "reported": 30,
            "disaggregationLocationCamp": 200,
            "disaggregationLocationNonCamp": 10,
        })
        mock_bulk_update_figure_manager_add_event.assert_not_called()
        mock_bulk_update_figure_manager_exit.assert_not_called()
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [figure_item_input],
                "delete_ids": [],
            }
        )
        assert mock_bulk_update_figure_manager_add_event.call_count == 0
        assert mock_bulk_update_figure_manager_exit.call_count == 1
        content_data = response.json()['data']['bulkUpdateFigures']
        self.assertIn('disaggregationLocationCamp', get_first_error_fields(content_data['errors']))
        self.assertIn('disaggregationLocationNonCamp', get_first_error_fields(content_data['errors']))

        figure_item_input.update({
            "reported": 300,
            "disaggregationLocationCamp": 200,
            "disaggregationLocationNonCamp": 100,
        })
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [figure_item_input],
                "delete_ids": [],
            }
        )
        assert mock_bulk_update_figure_manager_add_event.call_count == 1
        mock_bulk_update_figure_manager_add_event.assert_has_calls([call(self.event.id)])
        assert mock_bulk_update_figure_manager_exit.call_count == 2
        content_data = response.json()['data']['bulkUpdateFigures']

    def test_invalid_figures_household_size(
        self,
        mock_bulk_update_figure_manager_exit,
        mock_bulk_update_figure_manager_add_event,
    ):
        """
        If unit is househod, household_size must be supplied.
        """
        self.f3.household_size = None
        self.f3.save()

        figure_item_input = copy(self.figure_item_input)
        figure_item_input.update({
            "unit": Figure.UNIT.HOUSEHOLD.name,  # missing household_size
        })
        mock_bulk_update_figure_manager_add_event.assert_not_called()
        mock_bulk_update_figure_manager_exit.assert_not_called()
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [figure_item_input],
                "delete_ids": [],
            }
        )
        mock_bulk_update_figure_manager_add_event.assert_not_called()
        mock_bulk_update_figure_manager_exit.assert_called_once()
        content_data = response.json()['data']['bulkUpdateFigures']
        assert 'householdSize' in get_first_error_fields(content_data['errors'])

    def test_invalid_figures_age_data(
        self,
        mock_bulk_update_figure_manager_exit,
        mock_bulk_update_figure_manager_add_event,
    ):
        figure_item_input = copy(self.figure_item_input)
        figure_item_input.update({
            "disaggregationAge": [
                # invalid: category and sex is duplicated
                {
                    "uuid": "e4857d07-736c-4ff3-a21f-51170f0551c9",
                    "ageFrom": 10,
                    "ageTo": 20,
                    "sex": "MALE",
                    "value": 5
                },
                {
                    "uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce",
                    "ageFrom": 10,
                    "ageTo": 20,
                    "sex": "MALE",
                    "value": 5
                }
            ],
        })
        mock_bulk_update_figure_manager_add_event.assert_not_called()
        mock_bulk_update_figure_manager_exit.assert_not_called()
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [figure_item_input],
                "delete_ids": [],
            }
        )
        mock_bulk_update_figure_manager_add_event.assert_not_called()
        mock_bulk_update_figure_manager_exit.assert_called_once()
        content_data = response.json()['data']['bulkUpdateFigures']
        assert content_data['result'] == [None]
        assert 'disaggregationAge' in get_first_error_fields(content_data['errors'])

    def test_figure_cause_should_be_same_as_event_type(self, *_):
        event_1 = EventFactory.create(event_type=Crisis.CRISIS_TYPE.CONFLICT)
        event_2 = EventFactory.create(event_type=Crisis.CRISIS_TYPE.DISASTER)
        event_3 = EventFactory.create(event_type=Crisis.CRISIS_TYPE.OTHER)

        # Make copies of input
        figure_input_1 = copy(self.figure_item_input)
        figure_input_2 = copy(self.figure_item_input)
        figure_input_3 = copy(self.figure_item_input)

        # Pass incorrect figure cause and test
        figure_input_1.update({
            'figureCause': Crisis.CRISIS_TYPE.DISASTER.name,
            'event': event_1.id,
        })
        figure_input_2.update({
            'figureCause': Crisis.CRISIS_TYPE.OTHER.name,
            'event': event_2.id,
        })
        figure_input_3.update({
            'figureCause': Crisis.CRISIS_TYPE.CONFLICT.name,
            'event': event_3.id,
        })
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [figure_input_1, figure_input_2, figure_input_3],
                "delete_ids": [],
            }
        )
        content_data = response.json()['data']['bulkUpdateFigures']
        self.assertResponseNoErrors(response)
        assert 'figureCause' in get_first_error_fields(content_data['errors'])

        # Pass correct figure cause and test
        figure_input_1.update({
            'figureCause': Crisis.CRISIS_TYPE.CONFLICT.name,
            'event': event_1.id,
        })
        figure_input_2.update({
            'figureCause': Crisis.CRISIS_TYPE.DISASTER.name,
            'event': event_2.id,
        })
        figure_input_3.update({
            'figureCause': Crisis.CRISIS_TYPE.OTHER.name,
            'event': event_3.id,
        })
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [figure_input_1, figure_input_2, figure_input_3],
                "delete_ids": [],
            }
        )
        content_data = response.json()['data']['bulkUpdateFigures']
        self.assertResponseNoErrors(response)
        assert 'figureCause' not in get_first_error_fields(content_data['errors'])

    def test_figure_include_idu_validation(self, *_):
        """
        If includeIdu is True, excerptIdu must be provided.
        """
        # Pass invalid input and test
        figure_item_input = copy(self.figure_item_input)
        figure_item_input.update({
            'includeIdu': True, 'excerptIdu': '  ',
        })
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [figure_item_input],
                "delete_ids": [],
            }
        )
        content_data = response.json()['data']['bulkUpdateFigures']
        assert 'excerptIdu' in get_first_error_fields(content_data['errors'])

        # Pass correct value and test
        figure_item_input.update({
            'includeIdu': False, 'excerptIdu': '  ',
        })
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [figure_item_input],
                "delete_ids": [],
            }
        )
        content_data = response.json()['data']['bulkUpdateFigures']
        assert 'excerptIdu' not in get_first_error_fields(content_data['errors'])

    @patch('apps.entry.serializers.send_event_notifications')
    def test_should_update_event_in_figure(
        self,
        serializer_notification_send,
        mock_bulk_update_figure_manager_exit,
        mock_bulk_update_figure_manager_add_event,
    ):
        entry = EntryFactory.create()
        event1, event2, event3 = EventFactory.create_batch(
            3,
            countries=[self.country_1],
            review_status=Event.EVENT_REVIEW_STATUS.SIGNED_OFF,
        )
        figure1 = FigureFactory.create(entry=entry, event=event1)
        figure2 = FigureFactory.create(entry=entry, event=event2)

        def _get_mock_call_arg(mock):
            return [
                (
                    call.args[0].id,  # Figure
                    call.args[1].id,  # User
                    call.args[2],  # Type
                )
                for call in mock.mock_calls
            ]

        def _reset_mock():
            mock_bulk_update_figure_manager_add_event.reset_mock()
            mock_bulk_update_figure_manager_exit.reset_mock()
            serializer_notification_send.reset_mock()

        for _event in [event1, event2, event3]:
            _event.countries.add(self.country_1, self.country_2)

        # Make copies of input
        figure_input_1 = copy(self.figure_item_input)
        figure_input_2 = copy(self.figure_item_input)

        # Test with correct event ids
        figure_input_1.update({
            'id': figure1.id,
            'event': event1.id,
        })
        figure_input_2.update({
            'id': figure2.id,
            'event': event2.id,
        })
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [figure_input_1, figure_input_2],
                "delete_ids": [],
            }
        )
        assert mock_bulk_update_figure_manager_add_event.call_count == 2
        mock_bulk_update_figure_manager_add_event.assert_has_calls([
            call(event1.id),
            call(event2.id),
        ], any_order=True)
        mock_bulk_update_figure_manager_exit.assert_called_once()
        self.assertResponseNoErrors(response)
        content_data = response.json()['data']['bulkUpdateFigures']
        self.assertNotIn('event', get_first_error_fields(content_data['errors']))
        self.assertNotEqual(content_data['result'], [None, None])
        # Notification check - Should be empty
        assert _get_mock_call_arg(serializer_notification_send) == []
        _reset_mock()

        for event_review_status, have_figure_move_notification in [
            [Event.EVENT_REVIEW_STATUS.SIGNED_OFF, True],
            [Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED, True],
            [Event.EVENT_REVIEW_STATUS.APPROVED, True],
            [Event.EVENT_REVIEW_STATUS.APPROVED, True],
            [Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED, True],
            [Event.EVENT_REVIEW_STATUS.REVIEW_NOT_STARTED, False],
            [Event.EVENT_REVIEW_STATUS.REVIEW_IN_PROGRESS, False],
        ]:
            # Change event status
            for event in [event1, event2, event3]:
                event.review_status = event_review_status
                event.save()
            # Rest figure2 event to event2
            figure2.event = event2
            figure2.save()
            # Test with changed event ids
            figure_input_1.update({
                'id': figure1.id,
                'event': event1.id,
            })
            figure_input_2.update({
                'id': figure2.id,
                'event': event3.id,
            })
            response = self.query(
                self.figure_bulk_mutation,
                variables={
                    "items": [figure_input_1, figure_input_2],
                    "delete_ids": [],
                }
            )
            self.assertResponseNoErrors(response)
            assert mock_bulk_update_figure_manager_add_event.call_count == 3
            mock_bulk_update_figure_manager_add_event.assert_has_calls([
                # Figure 1 - Figure changed
                call(event1.id),
                # Figure 2 - Figure moved
                call(event2.id),  # Existing event
                call(event3.id),  # New event
            ])
            # Notification check
            if have_figure_move_notification:
                notification_types = (
                    (Notification.Type.FIGURE_DELETED_IN_SIGNED_EVENT, Notification.Type.FIGURE_CREATED_IN_SIGNED_EVENT)
                    if event_review_status in [
                        Event.EVENT_REVIEW_STATUS.SIGNED_OFF,
                        Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED,
                    ]
                    else
                    (Notification.Type.FIGURE_DELETED_IN_APPROVED_EVENT, Notification.Type.FIGURE_CREATED_IN_APPROVED_EVENT)
                )
                assert _get_mock_call_arg(serializer_notification_send) == [
                    # Deleted in event2
                    (event2.pk, self.editor.id, notification_types[0]),
                    # Created in event2
                    (event3.pk, self.editor.id, notification_types[1]),
                ]
            else:
                assert _get_mock_call_arg(serializer_notification_send) == []
            mock_bulk_update_figure_manager_exit.assert_called_once()
            _reset_mock()

        content_data = response.json()['data']['bulkUpdateFigures']
        self.assertNotIn('event', get_first_error_fields(content_data['errors']))
        self.assertEqual(str(event1.id), content_data['result'][0]['event']['id'])
        self.assertEqual(event1.name, content_data['result'][0]['event']['name'])
        self.assertEqual(str(event3.id), content_data['result'][1]['event']['id'])
        self.assertEqual(event3.name, content_data['result'][1]['event']['name'])

    def test_bulk_update_batch_size(self, *_):
        figure_item_input = copy(self.figure_item_input)
        payload = {
            "items": [figure_item_input] * 3,
            "delete_ids": [1, 2],
        }
        with override_settings(GRAPHENE_BATCH_DEFAULT_MAX_LIMIT=4):
            response = self.query(self.figure_bulk_mutation, variables=payload)
            content_data = response.json()['data']['bulkUpdateFigures']
            self.assertResponseErrors(response)
            assert content_data is None
            # Unit test
            with self.assertRaises(PermissionDenied) as exc:
                BulkUpdateFigures.validate_batch_size([1] * 3, [1, 2])
            assert (
                str(exc.exception) == (
                    'Max limit for batch is 4. But 5 where provided.'
                    ' Where CREATE/UPDATE = 3 and DELETE = 2'
                )
            )
        with override_settings(GRAPHENE_BATCH_DEFAULT_MAX_LIMIT=6):
            response = self.query(self.figure_bulk_mutation, variables=payload)
            content_data = response.json()['data']['bulkUpdateFigures']
            self.assertResponseNoErrors(response)
            assert content_data is not None
            # Unit test
            BulkUpdateFigures.validate_batch_size([1] * 3, [1, 2])

    @patch('apps.entry.mutations.send_figure_notifications')
    @patch('apps.entry.serializers.send_figure_notifications')
    def test_bulk_update_notification_test(self, serializer_send, mutation_send, *_):
        figure_item_input = copy(self.figure_item_input)
        payload = {
            "items": [figure_item_input] * 3,   # Change fig3 only
            "delete_ids": [self.f1.pk, self.f2.pk],
        }
        self.event.review_status = Event.EVENT_REVIEW_STATUS.SIGNED_OFF
        self.event.save()
        response = self.query(self.figure_bulk_mutation, variables=payload)
        self.assertResponseNoErrors(response)

        def _get_mock_call_arg(mock):
            return [
                (
                    call.args[0].id,  # Figure
                    call.args[1].id,  # User
                    call.args[2],  # Type
                )
                for call in mock.mock_calls
            ]

        # Check
        # -- Call within serializer (Update)
        assert _get_mock_call_arg(serializer_send) == [
            (
                item['id'],
                self.editor.id,
                Notification.Type.FIGURE_UPDATED_IN_SIGNED_EVENT,
            )
            for item in payload['items']
        ]
        # -- Call within mutation class (Delete)
        assert _get_mock_call_arg(mutation_send) == [
            (
                id,
                self.editor.id,
                Notification.Type.FIGURE_DELETED_IN_SIGNED_EVENT,
            )
            for id in payload['delete_ids']
        ]
