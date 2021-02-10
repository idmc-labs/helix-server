from datetime import datetime, timedelta
import json
from uuid import uuid4

from apps.entry.models import (
    Figure,
    Entry,
    EntryReviewer,
    CANNOT_UPDATE_MESSAGE,
    OSMName,
)
from apps.entry.constants import STOCK, FLOW
from apps.users.enums import USER_ROLE
from utils.factories import (
    EventFactory,
    EntryFactory,
    FigureFactory,
    OrganizationFactory,
    CountryFactory,
    FigureCategoryFactory,
)
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestEntryQuery(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country = CountryFactory.create()
        self.country_id = str(self.country.id)
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        self.entry = EntryFactory.create(
            created_by=self.editor
        )
        self.entry_query = '''
        query MyQuery($id: ID!, $data: TotalFigureFilterInputType) {
          entry(id: $id) {
            totalStockFigures(data: $data)
            totalFlowFigures
          }
        }
        '''

    def test_figure_count_filtered_resolvers(self):
        self.fig_cat = FigureCategoryFactory.create(type=STOCK)
        self.fig_cat_id = str(self.fig_cat.id)
        self.fig_cat2 = FigureCategoryFactory.create(type=STOCK)
        self.fig_cat_id2 = str(self.fig_cat2.id)
        self.fig_cat3 = FigureCategoryFactory.create(type=FLOW)
        self.fig_cat_id3 = str(self.fig_cat3.id)
        figure1 = FigureFactory.create(entry=self.entry,
                                       category=self.fig_cat,
                                       reported=100,
                                       unit=Figure.UNIT.PERSON)
        figure2 = FigureFactory.create(entry=self.entry,
                                       category=self.fig_cat,
                                       reported=100,
                                       unit=Figure.UNIT.PERSON)
        figure3 = FigureFactory.create(entry=self.entry,
                                       category=self.fig_cat2,
                                       reported=50,
                                       unit=Figure.UNIT.PERSON)
        figure4 = FigureFactory.create(entry=self.entry,
                                       category=self.fig_cat3,
                                       reported=70,
                                       unit=Figure.UNIT.PERSON)
        response = self.query(
            self.entry_query,
            variables=dict(
                id=str(self.entry.id),
                data=dict(categories=[self.fig_cat_id])
            )
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        self.assertEqual(
            content['data']['entry']['totalStockFigures'],
            figure1.total_figures + figure2.total_figures
        )
        self.assertEqual(
            content['data']['entry']['totalStockFigures'],
            figure1.total_figures + figure2.total_figures
        )
        self.assertEqual(
            content['data']['entry']['totalFlowFigures'],
            figure4.total_figures
        )
        response = self.query(
            self.entry_query,
            variables=dict(
                id=str(self.entry.id),
                data=dict(categories=[self.fig_cat_id2])
            )
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        self.assertEqual(
            content['data']['entry']['totalStockFigures'],
            figure3.total_figures
        )


class TestCreateFigure(HelixGraphQLTestCase):
    def setUp(self):
        self.creator = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        self.country = CountryFactory.create(country_code=123)
        self.entry = EntryFactory.create(
            created_by=self.creator,
        )

        self.fig_cat = FigureCategoryFactory.create()
        self.mutation = """
            mutation CreateFigure($input: FigureCreateInputType!) {
                createFigure(data: $input) {
                    ok
                    errors
                    result {
                        id
                    }
                }
            }
        """
        self.input = {
            "entry": self.entry.id,
            "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
            "reported": 10,
            "unit": Figure.UNIT.PERSON.name,
            "term": Figure.TERM.EVACUATED.name,
            "category": self.fig_cat.id,
            "role": Figure.ROLE.RECOMMENDED.name,
            "startDate": "2020-10-10",
            "includeIdu": True,
            "excerptIdu": "excerpt abc",
            "country": self.country.id,
        }
        self.force_login(self.creator)

    def test_valid_create_figures(self):
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createFigure']['ok'], content)
        self.assertIsNone(content['data']['createFigure']['errors'], content)
        self.assertIsNotNone(content['data']['createFigure']['result']['id'])

    def test_invalid_geo_locations(self):
        self.input['geoLocations'] = [
            {
                "country": "Nepal",
                "countryCode": "23",
                "osmId": "tets1",
                "osmType": "HA",
                "identifier": OSMName.IDENTIFIER.ORIGIN.name,
                "displayName": "testname",
                "lon": 12.34,
                "lat": 23.21,
                "name": "testme",
                "accuracy": OSMName.OSM_ACCURACY.COUNTRY.name,
                "uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce",
                "boundingBox": [1.2],
            },
            {
                "country": "Nepal",
                "countryCode": "423",
                "osmId": "tets1",
                "osmType": "HA",
                "identifier": OSMName.IDENTIFIER.ORIGIN.name,
                "displayName": "testname",
                "lon": 12.34,
                "lat": 23.21,
                "name": "testme",
                "accuracy": OSMName.OSM_ACCURACY.COUNTRY.name,
                "uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce",
                "boundingBox": [1.2],
            },
        ]
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['createFigure']['ok'], content)
        self.assertIn('geoLocations', [item['field'] for item in content['data']['createFigure']['errors']], content)


class TestFigureUpdate(HelixGraphQLTestCase):
    def setUp(self):
        self.creator = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        self.entry = EntryFactory.create(
            created_by=self.creator
        )
        self.figure = FigureFactory.create(
            created_by=self.creator,
            entry=self.entry
        )
        self.mutation = '''
            mutation UpdateFigure($input: FigureUpdateInputType!) {
                updateFigure(data: $input) {
                    ok
                    result {
                        id
                        ageJson{
                            ageFrom
                            uuid
                            ageTo
                            value
                        }
                        strataJson{
                            date
                            value
                            uuid
                        }
                    }
                    errors
                }
            }
        '''
        self.input = {
            "id": self.figure.id,
            "ageJson": [
                {
                    "uuid": "e4857d07-736c-4ff3-a21f-51170f0551c9",
                    "ageFrom": 1,
                    "ageTo": 3,
                    "value": 13
                },
                {
                    "uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce",
                    "ageFrom": 3,
                    "ageTo": 5,
                    "value": 23
                }
            ],
            "strataJson": [
                {"date": "2020-10-10", "value": 12, "uuid": "132acc8b-b7f7-4535-8c80-f6eb35bf9003"},
                {"date": "2020-10-12", "value": 12, "uuid": "bf2b1415-2fc5-42b7-9180-a5b440e5f6d1"}
            ]
        }
        self.force_login(self.creator)

    def test_valid_figure_update(self):
        self.assertIsNone(self.figure.age_json)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateFigure']['ok'], content)
        self.assertIsNotNone(content['data']['updateFigure']['result']['id'], content)
        self.figure.refresh_from_db()
        self.assertEqual(len(self.figure.age_json), len(self.input['ageJson']))
        self.assertEqual(len(self.figure.strata_json), len(self.input['strataJson']))

    def test_invalid_age_groups_data(self):
        input1 = {
            "id": self.figure.id,
            "ageJson": [
                {
                    "uuid": str(uuid4()),
                    "ageFrom": 30,
                    "ageTo": 1,
                    "value": 13
                },
            ]
        }
        response = self.query(
            self.mutation,
            input_data=input1
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['updateFigure']['ok'], content)
        self.assertEqual('ageTo', content['data']['updateFigure']['errors'][0]['arrayErrors'][0]['objectErrors'][0]['field'])

        input2 = {
            "id": self.figure.id,
            "ageJson": [
                {
                    "uuid": str(uuid4()),
                    "ageFrom": 10,
                    "ageTo": 30,
                    "value": 13
                },
                {
                    "uuid": str(uuid4()),
                    "ageFrom": 20,
                    "ageTo": 40,
                    "value": 23
                }
            ]
        }
        response = self.query(
            self.mutation,
            input_data=input2
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['updateFigure']['ok'], content)
        self.assertEqual('ageJson',
                         content['data']['updateFigure']['errors'][0]['field'],
                         content)
        self.assertIsNotNone(content['data']['updateFigure']['errors'][0]['arrayErrors'][0]['messages'], content)


class TestEntryCreation(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country = CountryFactory.create()
        self.country_id = str(self.country.id)
        self.fig_cat = FigureCategoryFactory.create()
        self.fig_cat_id = str(self.fig_cat.id)
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        self.event = EventFactory.create()
        self.mutation = """
            mutation CreateEntry($input: EntryCreateInputType!) {
                createEntry(data: $input) {
                    ok
                    errors
                    result {
                        id
                        figures {
                            results {
                                id
                            }
                            totalCount
                        }
                        reviewers {
                            results {
                                id
                            }
                        }
                    }
                }
            }
        """
        self.input = {
            "url": "https://yoko-onos-blog.com",
            "articleTitle": "title 1",
            "sources": [str(OrganizationFactory.create().id)],
            "publishers": [str(OrganizationFactory.create().id)],
            "publishDate": "2020-09-09",
            "sourceExcerpt": "excerpt one",
            "idmcAnalysis": "analysis one",
            "isConfidential": True,
            "calculationLogic": "methoddddd",
            "reviewers": [],
            "event": self.event.id,
        }
        self.force_login(self.editor)

    def test_valid_create_entry_without_figures(self):
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createEntry']['ok'], content)
        self.assertIsNone(content['data']['createEntry']['errors'], content)
        self.assertIsNotNone(content['data']['createEntry']['result']['id'])

    def test_valid_nested_figures_create(self):
        figures = [
            {
                "uuid": str(uuid4()),
                "country": self.country_id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 10,
                "unit": Figure.UNIT.PERSON.name,
                "term": Figure.TERM.EVACUATED.name,
                "category": self.fig_cat_id,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2020-10-10",
                "includeIdu": True,
                "excerptIdu": "excerpt abc",
            }
        ]
        self.input.update({
            'figures': figures
        })
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createEntry']['ok'], content)
        self.assertIsNone(content['data']['createEntry']['errors'], content)
        self.assertIsNotNone(content['data']['createEntry']['result']['id'])
        self.assertEqual(content['data']['createEntry']['result']['figures']['totalCount'],
                         len(figures))
        self.assertIsNotNone(content['data']['createEntry']['result']['figures']['results'][0]['id'])

    def test_assert_nested_figures_errors(self):
        uuid = str(uuid4())
        uuid_error = str(uuid4())
        figures = [
            # valid data
            {
                "uuid": uuid,
                "country": self.country_id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 10,
                "unit": Figure.UNIT.PERSON.name,
                "term": Figure.TERM.EVACUATED.name,
                "category": self.fig_cat_id,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2020-10-10",
                "includeIdu": True,
                "excerptIdu": "excerpt abc",
            },
            # invalid now
            {
                "uuid": uuid_error,
                "country": self.country_id,
                "reported": -1,  # this cannot be negative
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "unit": Figure.UNIT.PERSON.name,
                "term": Figure.TERM.EVACUATED.name,
                "category": self.fig_cat_id,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2020-10-10",
                "includeIdu": True,
                "excerptIdu": "excerpt abc",
            }
        ]
        self.input.update({
            'figures': figures
        })
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['createEntry']['ok'], content)
        self.assertIsNotNone(content['data']['createEntry']['errors'], content)
        self.assertEqual('reported',
                         content['data']['createEntry']['errors'][0]['arrayErrors'][0]['objectErrors'][0]['field'])
        self.assertEqual(uuid_error,
                         content['data']['createEntry']['errors'][0]['arrayErrors'][0]['key'])

    def test_invalid_entry_created_by_reviewer(self):
        reviewer = create_user_with_role(role=USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])

    def test_add_reviewers_while_create_entry(self):
        r1 = create_user_with_role(role=USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        r2 = create_user_with_role(role=USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        r3 = create_user_with_role(role=USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.input.update(dict(reviewers=[str(r1.id), str(r2.id), str(r3.id)]))

        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = response.json()

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createEntry']['ok'], content)
        self.assertIsNone(content['data']['createEntry']['errors'], content)
        entry = Entry.objects.get(id=content['data']['createEntry']['result']['id'])
        self.assertEqual(entry.reviewers.count(), len(self.input['reviewers']))
        self.assertEqual(len(content['data']['createEntry']['result']['reviewers']
                             ['results']), len(self.input['reviewers']), content)

    def test_invalid_guest_entry_create(self):
        guest = create_user_with_role(role=USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])

    def test_invalid_figures_age_data(self):
        figures = [
            {
                "uuid": str(uuid4()),
                "country": self.country_id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 10,
                "unit": Figure.UNIT.PERSON.name,
                "householdSize": 1,
                "term": Figure.TERM.EVACUATED.name,
                "category": self.fig_cat_id,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2020-10-10",
                "includeIdu": True,
                "excerptIdu": "excerpt abc",
                "ageJson": [
                    # from is greater than to
                    {"uuid": "e4857d07-736c-4ff3-a21f-51170f0551c9", "ageFrom": 3, "ageTo": 2, "value": 3},
                    {"uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce", "ageFrom": 3, "ageTo": 5, "value": 3}
                ]
            }
        ]
        self.input.update({
            'figures': figures
        })
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['createEntry']['ok'], content)
        self.assertIn('ageTo', json.dumps(content['data']['createEntry']['errors']))

    def test_invalid_figures_household_size(self):
        figures = [
            {
                "uuid": str(uuid4()),
                "country": self.country_id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 10,
                "unit": Figure.UNIT.HOUSEHOLD.name,  # missing household_size
                "term": Figure.TERM.EVACUATED.name,
                "category": self.fig_cat_id,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2020-10-10",
                "includeIdu": True,
                "excerptIdu": "excerpt abc",
            }
        ]
        self.input.update({
            'figures': figures
        })
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['createEntry']['ok'], content)
        self.assertIn('householdSize', json.dumps(content['data']['createEntry']['errors']))


class TestEntryUpdate(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country = CountryFactory.create()
        self.country_id = str(self.country.id)
        self.fig_cat = FigureCategoryFactory.create()
        self.fig_cat_id = str(self.fig_cat.id)
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        self.entry = EntryFactory.create(
            created_by=self.editor
        )
        self.mutation = """
        mutation MyMutation($input: EntryUpdateInputType!) {
          updateEntry(data: $input) {
            ok
            errors
            result {
              id
              figures {
                results {
                  id
                  createdAt
                }
              }
              createdAt
              articleTitle
            }
          }
        }
        """
        self.input = {
            "id": self.entry.id,
            "articleTitle": "updated-bla",
        }

    def test_valid_update_entry(self):
        self.force_login(self.editor)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateEntry']['ok'], content)

    def test_invalid_update_by_reviewer(self):
        reviewer = create_user_with_role(role=USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])

    def test_invalid_entry_update_by_non_owner(self):
        self.editor2 = create_user_with_role(role=USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        self.force_login(self.editor2)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['updateEntry']['ok'], content)
        self.assertIn('nonFieldErrors',
                      [each['field'] for each in content['data']['updateEntry']['errors']])
        self.assertIn('You cannot update this entry',
                      json.dumps(content['data']['updateEntry']['errors']))

    def test_valid_entry_update_by_admins(self):
        admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(admin)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateEntry']['ok'], content)

    def test_valid_update_entry_with_figures(self):
        figure = FigureFactory.create(entry=self.entry)
        deleted_figure = FigureFactory.create(entry=self.entry)
        figures = [
            {
                "uuid": "1cd00034-037e-4c5f-b196-fa05b6bed803",
                "country": self.country_id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 10,
                "unit": Figure.UNIT.PERSON.name,
                "term": Figure.TERM.EVACUATED.name,
                "category": self.fig_cat_id,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2020-09-09",
                "includeIdu": False,
                "ageJson": [
                    {
                        "uuid": "e4857d07-736c-4ff3-a21f-51170f0551c9",
                        "ageFrom": 1,
                        "ageTo": 3,
                        "value": 3
                    },
                    {
                        "uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce",
                        "ageFrom": 3,
                        "ageTo": 5,
                        "value": 3
                    }
                ],
                "strataJson": [
                    {"date": "2020-10-10", "value": 12, "uuid": "132acc8b-b7f7-4535-8c80-f6eb35bf9003"},
                    {"date": "2020-10-12", "value": 12, "uuid": "bf2b1415-2fc5-42b7-9180-a5b440e5f6d1"}
                ]
            },
            {
                "id": figure.id,
                "uuid": str(figure.uuid),
                "country": self.country_id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 10,
                "unit": Figure.UNIT.PERSON.name,
                "term": Figure.TERM.EVACUATED.name,
                "category": self.fig_cat_id,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2020-09-09",
                "includeIdu": False,
                "ageJson": [
                    {
                        "uuid": "e4857d07-736c-4ff3-a21f-51170f0551c9",
                        "ageFrom": 1,
                        "ageTo": 3,
                        "value": 3
                    },
                    {
                        "uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce",
                        "ageFrom": 3,
                        "ageTo": 5,
                        "value": 3
                    }
                ],
                "strataJson": [
                    {"date": "2020-10-10", "value": 12, "uuid": "132acc8b-b7f7-4535-8c80-f6eb35bf9003"},
                    {"date": "2020-10-12", "value": 12, "uuid": "bf2b1415-2fc5-42b7-9180-a5b440e5f6d1"}
                ]
            },
        ]
        old_figures_count = self.entry.figures.count()

        self.force_login(self.editor)
        self.input['figures'] = figures
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateEntry']['ok'], content)
        self.entry.refresh_from_db()
        self.assertNotIn(deleted_figure, self.entry.figures.all())
        self.assertEqual(self.entry.figures.count(), old_figures_count)

    def test_invalid_figures_household_size(self):
        figures = [
            {
                "uuid": str(uuid4()),
                "country": self.country_id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 10,
                "unit": Figure.UNIT.HOUSEHOLD.name,  # missing household_size
                "term": Figure.TERM.EVACUATED.name,
                "category": self.fig_cat_id,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2020-10-10",
                "includeIdu": True,
                "excerptIdu": "excerpt abc",
            }
        ]
        self.input.update({
            'figures': figures
        })
        self.force_login(self.editor)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['updateEntry']['ok'], content)
        self.assertIn('householdSize', json.dumps(content['data']['updateEntry']['errors']))


class TestEntryDelete(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        self.entry = EntryFactory.create(
            created_by=self.editor
        )
        self.mutation = """
            mutation DeleteEntry($id: ID!) {
                deleteEntry(id: $id) {
                    ok
                    errors
                    result {
                        id
                        sources{
                          results {
                            id 
                          }
                        }
                        url
                        createdAt
                    }
                }
            }
        """
        self.variables = {
            "id": self.entry.id,
        }

    def test_valid_delete_entry(self):
        self.force_login(self.editor)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['deleteEntry']['ok'], content)
        self.assertEqual(content['data']['deleteEntry']['result']['url'],
                         self.entry.url)

    def test_invalid_delete_by_reviewer(self):
        reviewer = create_user_with_role(role=USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = json.loads(response.content)

        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])

    def test_invalid_entry_delete_by_non_owner(self):
        editor2 = create_user_with_role(role=USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        self.force_login(editor2)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['deleteEntry']['ok'], content)
        self.assertIn('nonFieldErrors',
                      [each['field'] for each in content['data']['deleteEntry']['errors']])
        self.assertIn('You cannot delete this entry',
                      json.dumps(content['data']['deleteEntry']['errors']))

    def test_valid_entry_delete_by_admins(self):
        admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(admin)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['deleteEntry']['ok'], content)
        self.assertEqual(content['data']['deleteEntry']['result']['url'],
                         self.entry.url)


class TestEntryReviewUpdate(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.entry = EntryFactory.create()
        self.r1 = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.r2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.r3 = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.it = create_user_with_role(USER_ROLE.IT_HEAD.name)
        self.entry.reviewers.set([self.r1, self.r2, self.r3, self.it])
        self.q = '''
        mutation MyMutation ($input: EntryReviewStatusInputType!){
          updateEntryReview(data: $input) {
            errors
            ok
          }
        }
        '''

    def test_update_review_status(self):
        input = dict(
            entry=str(self.entry.id),
            status=EntryReviewer.REVIEW_STATUS.UNDER_REVIEW.name
        )
        self.force_login(self.r1)
        response = self.query(
            self.q,
            input_data=input
        )
        content = response.json()

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateEntryReview']['ok'], content)

        # trying to signoff should fail
        input['status'] = EntryReviewer.REVIEW_STATUS.SIGNED_OFF.name
        response = self.query(
            self.q,
            input_data=input
        )
        content = response.json()

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['updateEntryReview']['ok'], content)
        self.assertIn(str(CANNOT_UPDATE_MESSAGE),
                      content['data']['updateEntryReview']['errors'][0]['messages'])

        # signoff by it head should succeed
        self.force_login(self.it)
        input['status'] = EntryReviewer.REVIEW_STATUS.SIGNED_OFF.name
        response = self.query(
            self.q,
            input_data=input
        )
        content = response.json()

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateEntryReview']['ok'], content)
