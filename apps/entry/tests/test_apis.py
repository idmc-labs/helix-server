import json

import pytest

from apps.crisis.models import Crisis
from apps.entry.models import (
    Figure,
)
from apps.users.enums import USER_ROLE
from utils.factories import (
    AttachmentFactory,
    ContextOfViolenceFactory,
    CountryFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
    OrganizationFactory,
    OrganizationKindFactory,
    TagFactory,
)
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, HelixTestCase, create_user_with_role, snapshot_in_class  # noqa: F401


class TestEntryQuery(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country = CountryFactory.create()
        self.country_id = str(self.country.id)
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.entry = EntryFactory.create(created_by=self.editor)
        self.entry_query = """
        query MyQuery($id: ID!) {
          entry(id: $id) {
            totalStockIdpFigures
            totalFlowNdFigures
          }
        }
        """
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)

    # def test_figure_count_filtered_resolvers(self):
    #     self.stock_fig_cat = Figure.FIGURE_CATEGORY_TYPES.IDPS
    #     self.random_fig_cat2 = Figure.FIGURE_CATEGORY_TYPES.CROSS_BORDER_FLIGHT
    #     self.flow_fig_cat3 = Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT
    #     self.event = EventFactory.create(
    #         event_type=Crisis.CRISIS_TYPE.OTHER.value,
    #     )
    #     self.event.countries.add(self.country)
    #     figure1 = FigureFactory.create(entry=self.entry,
    #                                    event=self.event,
    #                                    category=self.stock_fig_cat.value,
    #                                    reported=101,
    #                                    role=Figure.ROLE.RECOMMENDED,
    #                                    unit=Figure.UNIT.PERSON)
    #     FigureFactory.create(entry=self.entry,
    #                          category=self.stock_fig_cat.value,
    #                          event=self.event,
    #                          reported=102,
    #                          role=Figure.ROLE.TRIANGULATION,
    #                          unit=Figure.UNIT.PERSON)
    #     figure3 = FigureFactory.create(entry=self.entry,
    #                                    category=self.stock_fig_cat.value,
    #                                    reported=103,
    #                                    role=Figure.ROLE.RECOMMENDED,
    #                                    unit=Figure.UNIT.PERSON,
    #                                    event=self.event)
    #     FigureFactory.create(entry=self.entry,
    #                          event=self.event,
    #                          category=self.random_fig_cat2,
    #                          reported=50,
    #                          role=Figure.ROLE.RECOMMENDED,
    #                          unit=Figure.UNIT.PERSON)
    #     figure5 = FigureFactory.create(entry=self.entry,
    #                                    event=self.event,
    #                                    category=self.flow_fig_cat3,
    #                                    reported=70,
    #                                    role=Figure.ROLE.RECOMMENDED,
    #                                    unit=Figure.UNIT.PERSON)
    #     response = self.query(
    #         self.entry_query,
    #         variables=dict(
    #             id=str(self.entry.id),
    #         )
    #     )
    #     content = json.loads(response.content)
    #     self.assertResponseNoErrors(response)
    #     self.assertEqual(
    #         content['data']['entry']['totalStockIdpFigures'],
    #         figure1.total_figures + figure3.total_figures
    #     )
    #     self.assertEqual(
    #         content['data']['entry']['totalFlowNdFigures'],
    #         figure5.total_figures
    #     )
    # category based filter for entry stock/flow figures will not be used,
    # since it is directly filtered by IDP or INTERNAL DISPLACEMENT


class TestEntryCreation(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country = CountryFactory.create(iso2="lo", iso3="lol")
        self.country_id = str(self.country.id)
        self.event = EventFactory.create(event_type=Crisis.CRISIS_TYPE.CONFLICT.value)
        self.event.countries.add(self.country)
        self.fig_cat = Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.mutation = """
            mutation CreateEntry($input: EntryCreateInputType!) {
                createEntry(data: $input) {
                    ok
                    errors
                    result {
                        id
                        url
                        versionId
                        articleTitle
                        documentUrl
                        createdBy{
                            id
                            fullName
                        }
                    }
                }
            }
        """
        self.input = {
            "url": "https://yoko-onos-blog.com",
            "articleTitle": "title 1",
            "publishers": [str(OrganizationFactory.create().id)],
            "publishDate": "2020-09-09",
            "idmcAnalysis": "analysis one",
            "isConfidential": True,
        }
        self.force_login(self.editor)
        self.tag1 = TagFactory.create()
        self.tag2 = TagFactory.create()
        self.tag3 = TagFactory.create()
        self.context_of_violence = ContextOfViolenceFactory.create()

    def test_valid_create_entry(self):
        response = self.query(self.mutation, input_data=self.input)
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content["data"]["createEntry"]["ok"], content)
        self.assertIsNone(content["data"]["createEntry"]["errors"], content)
        self.assertIsNotNone(content["data"]["createEntry"]["result"]["id"])

    def test_invalid_guest_entry_create(self):
        guest = create_user_with_role(role=USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(self.mutation, input_data=self.input)
        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content["errors"][0]["message"])

    @pytest.mark.usefixtures("snapshot_in_class")
    def test_entry_validation(self) -> None:
        # both url and document cannot be set
        input_1 = self.input
        input_1["document"] = AttachmentFactory().id
        response = self.query(self.mutation, input_data=input_1)
        content = json.loads(response.content)
        assert content == self.snapshot
        assert not content["data"]["createEntry"]["ok"]

        # document url must be valid url
        input_2 = self.input
        input_2["document"] = AttachmentFactory().id
        input_2["documentUrl"] = ("www.invalidurl.com",)
        response = self.query(self.mutation, input_data=input_2)
        content = json.loads(response.content)
        assert content == self.snapshot
        assert not content["data"]["createEntry"]["ok"]

    def test_clear_fields(self):
        # if document not defined clear document url
        input_1 = self.input
        input_1["document"] = None
        input_1["documentUrl"] = "https://www.test.com"
        response = self.query(self.mutation, input_data=input_1)
        content = json.loads(response.content)
        assert not content["data"]["createEntry"]["result"]["documentUrl"]


class TestEntryUpdate(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country = CountryFactory.create(iso2="np")
        self.country_id = str(self.country.id)
        self.fig_cat = Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT)
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.event = EventFactory.create(name="myevent", event_type=Crisis.CRISIS_TYPE.CONFLICT.value)
        self.event.countries.add(self.country)
        self.entry = EntryFactory.create(
            created_by=self.editor,
        )
        self.mutation = """
        mutation MyMutation($input: EntryUpdateInputType!) {
          updateEntry(data: $input) {
            ok
            errors
            result {
              id
              createdAt
              articleTitle
              documentUrl
              createdBy {
                  id
                  fullName
              }
            }
          }
        }
        """
        self.input = {
            "id": self.entry.id,
            "articleTitle": "updated-bla",
        }

    def test_valid_update_entry(self):
        self.force_login(self.admin)
        response = self.query(self.mutation, input_data=self.input)
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content["data"]["updateEntry"]["ok"], content)

    def test_valid_entry_update_by_admins(self):
        self.force_login(self.admin)
        response = self.query(self.mutation, input_data=self.input)
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content["data"]["updateEntry"]["ok"], content)

    @pytest.mark.usefixtures("snapshot_in_class")
    def test_entry_validation(self) -> None:
        self.force_login(self.admin)

        # both url and document cannot be set
        input_1 = self.input
        input_1["document"] = AttachmentFactory().id
        response = self.query(self.mutation, input_data=input_1)
        content = json.loads(response.content)
        assert content == self.snapshot
        assert not content["data"]["updateEntry"]["ok"]

        # document url must be valid url
        input_2 = self.input
        input_2["document"] = AttachmentFactory().id
        input_2["documentUrl"] = ("www.invalidurl.com",)
        response = self.query(self.mutation, input_data=input_2)
        content = json.loads(response.content)
        assert content == self.snapshot
        assert not content["data"]["updateEntry"]["ok"]

    def test_entry_clear_fields(self):
        self.force_login(self.admin)
        # if document not defined clear document url
        input_1 = self.input
        input_1["document"] = None
        input_1["documentUrl"] = "https://www.test.com"
        response = self.query(self.mutation, input_data=input_1)
        content = json.loads(response.content)
        assert not content["data"]["updateEntry"]["result"]["documentUrl"]


class TestEntryDelete(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.entry = EntryFactory.create(created_by=self.editor)
        self.mutation = """
            mutation DeleteEntry($id: ID!) {
                deleteEntry(id: $id) {
                    ok
                    errors
                    result {
                        id
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
        response = self.query(self.mutation, variables=self.variables)
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content["data"]["deleteEntry"]["ok"], content)
        self.assertEqual(content["data"]["deleteEntry"]["result"]["url"], self.entry.url)

    def test_valid_entry_delete_by_admins(self):
        admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(admin)
        response = self.query(self.mutation, variables=self.variables)
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content["data"]["deleteEntry"]["ok"], content)
        self.assertEqual(content["data"]["deleteEntry"]["result"]["url"], self.entry.url)


class TestExportEntry(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        for _ in range(3):
            EntryFactory.create(created_by=self.editor)
        self.mutation = """
        mutation ExportEntries($filterFigureStartAfter: Date, $filterFigureEndBefore: Date){
            exportEntries(
                filters: {
                    filterFigureStartAfter: $filterFigureStartAfter
                    filterFigureEndBefore: $filterFigureEndBefore
                }
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
        response = self.query(self.mutation, variables=self.variables)
        self.assertResponseNoErrors(response)


class TestFigureDelete(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country = CountryFactory.create()
        self.country_id = str(self.country.id)
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.entry = EntryFactory.create(created_by=self.editor)
        self.event = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
        self.event.countries.add(self.country)
        self.figure = FigureFactory.create(
            entry=self.entry,
            reported=101,
            role=Figure.ROLE.RECOMMENDED,
            unit=Figure.UNIT.PERSON,
            event=self.event,
        )
        self.mutation = """
            mutation DeleteFigure($id: ID!) {
                deleteFigure(id: $id) {
                    ok
                    errors
                    result {
                        id
                    }
                }
            }
        """
        self.variables = {
            "id": self.figure.id,
        }

    def test_can_delete_figure(self):
        self.force_login(self.editor)
        response = self.query(self.mutation, variables=self.variables)
        self.assertResponseNoErrors(response)

        content = json.loads(response.content)
        self.assertTrue(content["data"]["deleteFigure"]["ok"], content)


class TestEntryTypeFields(HelixTestCase):
    def test_figures_is_not_exposed_on_entry_type(self):
        # The nested list was unbounded fan-out and no client used it; figures are
        # read via figureList(filterFigureEntry). Guard against re-adding it.
        from apps.entry.schema import EntryType

        self.assertNotIn("figures", EntryType._meta.fields)


class TestIDUGenerate(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(self.editor)
        self.org_kind_gov = OrganizationKindFactory.create(name="Government")
        self.org_kind_local_auth = OrganizationKindFactory.create(name="Local Authority")
        self.sources_1 = OrganizationFactory.create(organization_kind=self.org_kind_local_auth)
        self.sources_2 = OrganizationFactory.create(organization_kind=self.org_kind_gov)
        self.mutation = """
            mutation MyMutation($data: IDUGenerateInputType!) {
                generateIdu(data: $data) {
                    ok
                    result
                }
            }
        """

        self.variables = {
            "data": {
                "mainTrigger": Crisis.CRISIS_TYPE.DISASTER.name,
                "disasterSubType": "1",
                "violenceSubType": None,
                "otherSubType": None,
                "quantifier": Figure.QUANTIFIER.APPROXIMATELY.name,
                "figure": 1,
                "sources": [self.sources_1.id, self.sources_2.id],
                "displacementTerm": Figure.FIGURE_TERMS.PARTIALLY_DESTROYED_HOUSING.name,
                "locations": [
                    {
                        "id": "656496",
                        "uuid": "ee41e69a-addf-4953-bf46-f3e14d578c3e",
                        "accuracy": "ADM3",
                        "identifier": "ORIGIN",
                        "geocoder": "OSMNAME",
                        "boundingBox": [85.268105, 27.66795, 85.375557, 27.751339],
                        "city": "Kathmandu",
                        "className": "place",
                        "country": "Nepal",
                        "countryCode": "np",
                        "displayName": "Kathmandu, Kathmandu, Bagmati, Central Development Region, Nepal",
                        "houseNumbers": "",
                        "importance": 0.578457,
                        "lat": 27.709909,
                        "lon": 85.324753,
                        "moved": False,
                        "name": "Kathmandu",
                        "nameSuffix": "Kathmandu",
                        "osmId": "4853462",
                        "osmType": "relation",
                        "placeRank": 16,
                        "rank": 25802786,
                        "state": "Central Development Region",
                        "street": "",
                        "type": "city",
                        "wikiData": "Q3037",
                        "wikipedia": "en:Kathmandu",
                    }
                ],
                "startDate": "2025-01-11",
                "endDate": "2025-01-16",
                "unit": Figure.UNIT.HOUSEHOLD.name,
            }
        }

    def test_generate_idu_using_figure_data(self):
        response = self.query(self.mutation, variables=self.variables)
        self.assertResponseNoErrors(response)

        content = response.json()

        result_string = content["data"]["generateIdu"]["result"]

        expected_string = (
            "According to local authorities, around one household was reported "
            "partially destroyed housing in kathmandu, kathmandu, "
            "bagmati, central development region, nepal due to an earthquake "
            "between the 11th and 16th of january 2025.",
            "According to local authorities, about one household was reported "
            "partially destroyed housing in kathmandu, kathmandu, "
            "bagmati, central development region, nepal due to an earthquake "
            "between the 11th and 16th of january 2025.",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(content["data"]["generateIdu"]["ok"])
        self.assertIn(result_string, expected_string)

        input_1 = self.variables.copy()
        input_1["data"]["mainTrigger"] = Crisis.CRISIS_TYPE.CONFLICT.name
        input_1["data"]["violenceSubType"] = "2"
        input_1["data"]["figure"] = 10
        input_1["data"]["displacementTerm"] = Figure.FIGURE_TERMS.DISPLACED.name
        input_1["data"]["unit"] = Figure.UNIT.PERSON.name
        response = self.query(self.mutation, variables=self.variables)
        self.assertResponseNoErrors(response)
        content = response.json()
        result_string = content["data"]["generateIdu"]["result"]
        expected_string = (
            "According to local authorities, around 10 people were reported displaced "
            "in kathmandu, kathmandu, bagmati, central development region, nepal due to "
            "international armed conflict between the 11th and 30th of january 2025.",
            "According to local authorities, about 10 people were reported displaced in "
            "kathmandu, kathmandu, bagmati, central development region, nepal due to "
            "international armed conflict between the 11th and 30th of january 2025.",
        )
