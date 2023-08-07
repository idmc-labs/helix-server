import json
from copy import copy
from uuid import uuid4

from utils.tests import HelixGraphQLTestCase, create_user_with_role
from utils.factories import (
    EntryFactory,
    CountryFactory,
    EventFactory,
    FigureFactory,
)

from apps.crisis.models import Crisis
from apps.users.enums import USER_ROLE
from apps.entry.models import Figure, OSMName


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
            mutation BulkUpdateFigures($data: [FigureUpdateInputType!], $delete_ids: [ID!]) {
                bulkUpdateFigures(data: $data, deleteIds: $delete_ids) {
                    ok
                    errors
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

    def test_can_bulk_create_and_delete_figures(self):
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
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "data": figures,
                "delete_ids": figure_ids
            },
        )
        # Test bulk deleted
        self.assertEqual(Figure.objects.filter(id__in=figure_ids).count(), 0)

        # Test created
        content = json.loads(response.content)
        content_data = content['data']['bulkUpdateFigures']
        self.assertResponseNoErrors(response)
        self.assertTrue(content_data['ok'], True)
        self.assertIsNone(content_data['errors'], None)
        self.assertEqual(len(content_data['result']), 3)

        # Check each item
        for created_figure in content_data['result']:
            self.assertEqual(created_figure['figureCause'], Crisis.CRISIS_TYPE.CONFLICT.name)
            self.assertEqual(created_figure['includeIdu'], True)
            self.assertEqual(created_figure['entry']['id'], str(self.entry.id))

    def test_can_bulk_update_and_delete_figures(self):
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
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "data": figures,
                "delete_ids": figure_ids,
            },
        )

        # Test bulk deleted
        self.assertEqual(Figure.objects.filter(id__in=figure_ids).count(), 0)

        # Test updated
        content = json.loads(response.content)
        content_data = content['data']['bulkUpdateFigures']
        self.assertResponseNoErrors(response)
        self.assertTrue(content_data['ok'], True)
        self.assertIsNone(content_data['errors'], None)
        self.assertEqual(len(content_data['result']), 2)

        # Check each item
        for updated_figure in content_data['result']:
            self.assertEqual(updated_figure['figureCause'], Crisis.CRISIS_TYPE.CONFLICT.name)
            self.assertEqual(updated_figure['includeIdu'], False)
            self.assertEqual(updated_figure['entry']['id'], str(self.entry.id))

    def test_household_size_validation(self):
        """
        reported <= disaggregationLocationCamp + disaggregationLocationNonCamp
        """
        self.figure_item_input.update({
            "reported": 30,
            "disaggregationLocationCamp": 200,
            "disaggregationLocationNonCamp": 10,
        })
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "data": [self.figure_item_input],
                "delete_ids": [],
            }
        )
        content = json.loads(response.content)
        content_data = content['data']['bulkUpdateFigures']
        self.assertFalse(content_data['ok'], False)
        self.assertNotIn('disaggregationLocationCamp', content_data['errors'])
        self.assertNotIn('disaggregationLocationNonCamp', content_data['errors'])

        self.figure_item_input.update({
            "reported": 300,
            "disaggregationLocationCamp": 200,
            "disaggregationLocationNonCamp": 100,
        })
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "data": [self.figure_item_input],
                "delete_ids": [],
            }
        )
        content = json.loads(response.content)
        content_data = content['data']['bulkUpdateFigures']
        self.assertTrue(content_data['ok'], True)

    def test_invalid_figures_household_size(self):
        """
        If unit is househod, household_size must be supplied.
        """
        self.f3.household_size = None
        self.f3.save()

        self.figure_item_input.update({
            "unit": Figure.UNIT.HOUSEHOLD.name,  # missing household_size
        })
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "data": [self.figure_item_input],
                "delete_ids": [],
            }
        )
        content = json.loads(response.content)
        content_data = content['data']['bulkUpdateFigures']
        self.assertFalse(content_data['ok'], False)
        self.assertIn('household_size', content_data['errors'][0])

    def test_invalid_figures_age_data(self):
        self.figure_item_input.update({
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
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "data": [self.figure_item_input],
                "delete_ids": [],
            }
        )
        content = json.loads(response.content)
        content_data = content['data']['bulkUpdateFigures']
        self.assertFalse(content_data['ok'], False)
        self.assertIn('disaggregation_age', content_data['errors'][0])

    def test_figure_cause_should_be_same_as_event_type(self):
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
                "data": [figure_input_1, figure_input_2, figure_input_3],
                "delete_ids": [],
            }
        )
        content = json.loads(response.content)
        content_data = content['data']['bulkUpdateFigures']
        self.assertResponseNoErrors(response)
        self.assertFalse(content_data['ok'], True)
        self.assertIn('figure_cause', content_data['errors'][0])

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
                "data": [figure_input_1, figure_input_2, figure_input_3],
                "delete_ids": [],
            }
        )
        content = json.loads(response.content)
        content_data = content['data']['bulkUpdateFigures']
        self.assertResponseNoErrors(response)
        self.assertFalse(content_data['ok'], True)
        self.assertNotIn('figureCause', content_data['errors'])

    def test_figure_include_idu_validation(self):
        """
        If includeIdu is True, excerptIdu must be provided.
        """
        # Pass invalid input and test
        self.figure_item_input.update({
            'includeIdu': True, 'excerptIdu': '  ',
        })
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "data": [self.figure_item_input],
                "delete_ids": [],
            }
        )
        content = json.loads(response.content)
        content_data = content['data']['bulkUpdateFigures']
        self.assertFalse(content_data['ok'])
        self.assertIn('excerpt_idu', content_data['errors'][0])

        # Pass correct value and test
        self.figure_item_input.update({
            'includeIdu': False, 'excerptIdu': '  ',
        })
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "data": [self.figure_item_input],
                "delete_ids": [],
            }
        )
        content = json.loads(response.content)
        content_data = content['data']['bulkUpdateFigures']
        self.assertTrue(content_data['ok'], True)

    def test_should_update_event_in_figure(self):
        entry = EntryFactory.create()
        event1 = EventFactory.create(countries=[self.country_1])
        event2 = EventFactory.create(countries=[self.country_1])
        figure1 = FigureFactory.create(entry=entry, event=event1, country=self.country_1)

        # Make copies of input
        figure_input_1 = copy(self.figure_item_input)

        # Test with correct event ids
        figure_input_1.update({
            'id': figure1.id, 'event': event2.id,
        })
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "data": [figure_input_1],
                "delete_ids": [],
            }
        )
        self.assertResponseNoErrors(response)
        content = json.loads(response.content)
        content_data = content['data']['bulkUpdateFigures']
        self.assertTrue(content_data['ok'], content)
        self.assertEqual(str(event2.id), content_data['result'][0]['event']['id'])
        self.assertEqual(str(event2.name), content_data['result'][0]['event']['name'])
