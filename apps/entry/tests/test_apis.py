from copy import copy
import json
from uuid import uuid4

from apps.crisis.models import Crisis
from apps.entry.models import (
    Figure,
    FigureTerm,
    OSMName,
    Entry,
    EntryReviewer,
    CANNOT_UPDATE_MESSAGE,
    FigureCategory,
)
from apps.entry.models import DisaggregatedAgeCategory
from apps.entry.constants import FLOW
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
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.entry = EntryFactory.create(
            created_by=self.editor
        )
        self.entry_query = '''
        query MyQuery($id: ID!) {
          entry(id: $id) {
            totalStockIdpFigures
            totalFlowNdFigures
          }
        }
        '''
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)

    def test_figure_count_filtered_resolvers(self):
        FigureCategory._invalidate_category_ids_cache()
        self.stock_fig_cat = FigureCategory.stock_idp_id()
        self.stock_fig_cat_id = str(self.stock_fig_cat.id)
        self.random_fig_cat2 = FigureCategoryFactory.create(
            type=FLOW,
            name='lool',
        )
        self.random_fig_cat_id2 = str(self.random_fig_cat2.id)
        self.flow_fig_cat3 = FigureCategory.flow_new_displacement_id()
        self.flow_fig_cat_id3 = str(self.flow_fig_cat3.id)
        # XXX: only conflict figures are considered in stock (as of now)
        self.entry.event.event_type = Crisis.CRISIS_TYPE.CONFLICT
        self.entry.event.save()
        figure1 = FigureFactory.create(entry=self.entry,
                                       category=self.stock_fig_cat,
                                       reported=101,
                                       role=Figure.ROLE.RECOMMENDED,
                                       unit=Figure.UNIT.PERSON)
        FigureFactory.create(entry=self.entry,
                             category=self.stock_fig_cat,
                             reported=102,
                             role=Figure.ROLE.TRIANGULATION,
                             unit=Figure.UNIT.PERSON)
        figure3 = FigureFactory.create(entry=self.entry,
                                       category=self.stock_fig_cat,
                                       reported=103,
                                       role=Figure.ROLE.RECOMMENDED,
                                       unit=Figure.UNIT.PERSON)
        FigureFactory.create(entry=self.entry,
                             category=self.random_fig_cat2,
                             reported=50,
                             role=Figure.ROLE.RECOMMENDED,
                             unit=Figure.UNIT.PERSON)
        figure5 = FigureFactory.create(entry=self.entry,
                                       category=self.flow_fig_cat3,
                                       reported=70,
                                       role=Figure.ROLE.RECOMMENDED,
                                       unit=Figure.UNIT.PERSON)
        response = self.query(
            self.entry_query,
            variables=dict(
                id=str(self.entry.id),
            )
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        self.assertEqual(
            content['data']['entry']['totalStockIdpFigures'],
            figure1.total_figures + figure3.total_figures
        )
        self.assertEqual(
            content['data']['entry']['totalFlowNdFigures'],
            figure5.total_figures
        )
        # category based filter for entry stock/flow figures will not be used,
        # since it is directly filtered by IDP or NEW DISPLACEMENT


class TestEntryCreation(HelixGraphQLTestCase):
    def setUp(self) -> None:
        DisaggregatedAgeCategory.objects.create(name='one')
        DisaggregatedAgeCategory.objects.create(name='two')
        DisaggregatedAgeCategory.objects.create(name='three')
        self.country = CountryFactory.create(iso2='lo', iso3='lol')
        self.country_id = str(self.country.id)
        self.fig_cat = FigureCategoryFactory.create()
        self.fig_cat_id = str(self.fig_cat.id)
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.event = EventFactory.create()
        self.event.countries.add(self.country)
        self.mutation = """
            mutation CreateEntry($input: EntryCreateInputType!) {
                createEntry(data: $input) {
                    ok
                    errors
                    result {
                        id
                        figures {
                            id
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
        source1 = dict(
            uuid=str(uuid4()),
            rank=101,
            country=str(self.country.name),
            countryCode=self.country.iso2,
            osmId='ted',
            osmType='okay',
            displayName='okay',
            lat=68.88,
            lon=46.66,
            name='name',
            accuracy=OSMName.OSM_ACCURACY.ADM0.name,
            identifier=OSMName.IDENTIFIER.ORIGIN.name,
        )
        figures = [
            {
                "uuid": str(uuid4()),
                "country": self.country_id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 10,
                "unit": Figure.UNIT.PERSON.name,
                "term": str(FigureTerm.objects.first().id),
                "category": self.fig_cat_id,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2020-10-10",
                "includeIdu": True,
                "excerptIdu": "excerpt abc",
                "geoLocations": [source1],
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
        self.assertEqual(len(content['data']['createEntry']['result']['figures']),
                         len(figures))
        self.assertIsNotNone(content['data']['createEntry']['result']['figures'][0]['id'])

    def test_assert_nested_figures_errors(self):
        uuid = str(uuid4())
        uuid_error = str(uuid4())
        source1 = dict(
            uuid=str(uuid4()),
            rank=101,
            country=str(self.country.name),
            countryCode=self.country.iso2,
            osmId='ted',
            osmType='okay',
            displayName='okay',
            lat=68.88,
            lon=46.66,
            name='name',
            accuracy=OSMName.OSM_ACCURACY.ADM0.name,
            identifier=OSMName.IDENTIFIER.ORIGIN.name,
        )
        source2 = copy(source1)
        source2['lat'] = 67.5
        source2['uuid'] = str(uuid4())

        figures = [
            # valid data
            {
                "uuid": uuid,
                "country": self.country_id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 10,
                "unit": Figure.UNIT.PERSON.name,
                "term": str(FigureTerm.objects.first().id),
                "category": self.fig_cat_id,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2020-10-10",
                "includeIdu": True,
                "excerptIdu": "excerpt abc",
                "geoLocations": [source1],
            },
            # invalid now
            {
                "uuid": uuid_error,
                "country": self.country_id,
                "reported": -1,  # this cannot be negative
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "unit": Figure.UNIT.PERSON.name,
                "term": str(FigureTerm.objects.first().id),
                "category": self.fig_cat_id,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2020-10-10",
                "includeIdu": True,
                "excerptIdu": "excerpt abc",
                "geoLocations": [source2],
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
        self.assertEqual(uuid_error,
                         content['data']['createEntry']['errors'][0]['arrayErrors'][0]['key'],
                         content['data']['createEntry'])
        self.assertEqual('reported',
                         content['data']['createEntry']['errors'][0]['arrayErrors'][0]['objectErrors'][0]['field'])

    def test_add_reviewers_while_create_entry(self):
        r1 = create_user_with_role(role=USER_ROLE.MONITORING_EXPERT.name)
        r2 = create_user_with_role(role=USER_ROLE.MONITORING_EXPERT.name)
        r3 = create_user_with_role(role=USER_ROLE.MONITORING_EXPERT.name)
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
                "term": str(FigureTerm.objects.first().id),
                "category": self.fig_cat_id,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2020-10-10",
                "includeIdu": True,
                "excerptIdu": "excerpt abc",
                "disaggregationAgeJson": [
                    # invalid: category and sex is duplicated
                    {
                        "uuid": "e4857d07-736c-4ff3-a21f-51170f0551c9",
                        "category": DisaggregatedAgeCategory.objects.first().id,
                        "sex": 'MALE',
                        "value": 5
                    },
                    {
                        "uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce",
                        "category": DisaggregatedAgeCategory.objects.first().id,
                        "sex": 'MALE',
                        "value": 3
                    }
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
        self.assertIn('sex', json.dumps(content['data']['createEntry']['errors']))

    def test_invalid_figures_household_size(self):
        figures = [
            {
                "uuid": str(uuid4()),
                "country": self.country_id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 10,
                "unit": Figure.UNIT.HOUSEHOLD.name,  # missing household_size
                "term": str(FigureTerm.objects.first().id),
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
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.event = EventFactory.create(name='myevent')
        self.event.countries.add(self.country)
        DisaggregatedAgeCategory.objects.create(name='one')
        DisaggregatedAgeCategory.objects.create(name='two')
        DisaggregatedAgeCategory.objects.create(name='three')
        self.entry = EntryFactory.create(
            created_by=self.editor,
            event=self.event,
        )
        self.mutation = """
        mutation MyMutation($input: EntryUpdateInputType!) {
          updateEntry(data: $input) {
            ok
            errors
            result {
              id
              figures {
                id
                createdAt
                disaggregationAgeJson {
                  uuid
                  category {
                    id
                    name
                  }
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
        assert DisaggregatedAgeCategory.objects.count() > 1
        figure = FigureFactory.create(
            entry=self.entry,
            country=self.country
        )
        # this figure will be deleted
        deleted_figure = FigureFactory.create(entry=self.entry)
        source1 = dict(
            uuid=str(uuid4()),
            rank=101,
            country=str(self.country.name),
            countryCode=self.country.iso2,
            osmId='ted',
            osmType='okay',
            displayName='okay',
            lat=68.88,
            lon=46.66,
            name='name',
            accuracy=OSMName.OSM_ACCURACY.ADM0.name,
            identifier=OSMName.IDENTIFIER.ORIGIN.name,
        )
        source2 = copy(source1)
        source2['lat'] = 67.5
        source2['uuid'] = str(uuid4())
        figures = [
            {
                "uuid": "1cd00034-037e-4c5f-b196-fa05b6bed803",
                "country": self.country_id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 10,
                "unit": Figure.UNIT.PERSON.name,
                "term": str(FigureTerm.objects.first().id),
                "category": self.fig_cat_id,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2020-09-09",
                "includeIdu": False,
                "disaggregationAgeJson": [
                    {
                        "uuid": "e4857d07-736c-4ff3-a21f-51170f0551c9",
                        "category": DisaggregatedAgeCategory.objects.first().id,
                        "value": 3
                    },
                    {
                        "uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce",
                        "category": DisaggregatedAgeCategory.objects.last().id,
                        "value": 3
                    }
                ],
                "disaggregationStrataJson": [
                    {"date": "2020-10-10", "value": 2, "uuid": "132acc8b-b7f7-4535-8c80-f6eb35bf9003"},
                    {"date": "2020-10-12", "value": 2, "uuid": "bf2b1415-2fc5-42b7-9180-a5b440e5f6d1"}
                ],
                "geoLocations": [source1],
            },
            {
                "id": figure.id,
                "uuid": str(figure.uuid),
                "country": self.country_id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 10,
                "unit": Figure.UNIT.PERSON.name,
                "term": str(FigureTerm.objects.first().id),
                "category": self.fig_cat_id,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2020-09-09",
                "includeIdu": False,
                "disaggregationAgeJson": [
                    {
                        "uuid": "e4857d07-736c-4ff3-a21f-51170f0551c9",
                        "category": DisaggregatedAgeCategory.objects.first().id,
                        "value": 3
                    },
                    {
                        "uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce",
                        "category": DisaggregatedAgeCategory.objects.last().id,
                        "value": 3
                    }
                ],
                "disaggregationStrataJson": [
                    {"date": "2020-10-10", "value": 2, "uuid": "132acc8b-b7f7-4535-8c80-f6eb35bf9003"},
                    {"date": "2020-10-12", "value": 2, "uuid": "bf2b1415-2fc5-42b7-9180-a5b440e5f6d1"}
                ],
                "geoLocations": [source2],
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
                "term": str(FigureTerm.objects.first().id),
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
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
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
        self.r1 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.r2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.r3 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.it = create_user_with_role(USER_ROLE.ADMIN.name)
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


class TestExportEntry(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        for i in range(3):
            EntryFactory.create(created_by=self.editor)
        self.mutation = """
        mutation ExportEntries($filterFigureStartAfter: Date, $filterFigureEndBefore: Date){
            exportEntries(
                filterFigureStartAfter: $filterFigureStartAfter
                filterFigureEndBefore: $filterFigureEndBefore
          ){
            errors
            ok
          }
        }

        """
        self.variables = {
            "filterFigureStartAfter": "2018-08-25",
            "filterFigureEndBefore": "2021-08-25",
        }

    def test_export_entry(self):
        self.force_login(self.editor)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        self.assertResponseNoErrors(response)
