import json
from datetime import date

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.country.dataloaders import (
    CountryTotalFigureDisaggregationLoader,
    MonitoringSubRegionCountryCountLoader,
)
from apps.country.models import Country
from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.users.enums import USER_ROLE
from utils.factories import (
    ContactFactory,
    CountryFactory,
    EventFactory,
    FigureFactory,
    MonitoringSubRegionFactory,
)
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestMonitoringSubRegionCountryCountLoader(HelixGraphQLTestCase):
    """A batch's values are positional: value i belongs to keys[i], whatever order the
    underlying queryset returns its rows in and whether or not every key has a row.
    """

    def setUp(self) -> None:
        self.region_one, self.region_two, self.region_three = MonitoringSubRegionFactory.create_batch(3)
        # Distinct country counts, so a value landing on the wrong key is visible.
        CountryFactory.create_batch(1, monitoring_sub_region=self.region_one)
        CountryFactory.create_batch(2, monitoring_sub_region=self.region_two)
        CountryFactory.create_batch(3, monitoring_sub_region=self.region_three)
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))

    def test_values_follow_key_order(self) -> None:
        # Keys in descending id order, the order monitoringSubRegionList(ordering: "-id") hands
        # the loader, while the loader's own queryset is unordered.
        keys = [self.region_three.id, self.region_two.id, self.region_one.id]
        values = MonitoringSubRegionCountryCountLoader().batch_load_fn(keys).get()
        self.assertEqual(values, [3, 2, 1])

    def test_key_without_a_row_is_zero_and_does_not_shift_the_list(self) -> None:
        missing = self.region_one.id + self.region_two.id + self.region_three.id  # no such sub-region
        keys = [self.region_one.id, missing, self.region_three.id]
        values = MonitoringSubRegionCountryCountLoader().batch_load_fn(keys).get()
        self.assertEqual(values, [1, 0, 3])

    def test_graphql_list_reports_each_sub_regions_own_count(self) -> None:
        response = self.query(
            """
            query { monitoringSubRegionList(ordering: "-id") {
              results { id countriesCount }
            } }
            """
        )
        self.assertResponseNoErrors(response)
        results = json.loads(response.content)["data"]["monitoringSubRegionList"]["results"]
        counts = {row["id"]: row["countriesCount"] for row in results}
        self.assertEqual(counts[str(self.region_one.id)], 1)
        self.assertEqual(counts[str(self.region_two.id)], 2)
        self.assertEqual(counts[str(self.region_three.id)], 3)


class TestTwoRelationsToTheSameChild(HelixGraphQLTestCase):
    """Country.contacts and Country.operatingContacts both count Contact rows for the same
    parent id, and count different ones: each needs its own FilteredRelationCountLoader.
    """

    def setUp(self) -> None:
        self.country = CountryFactory.create()
        other_country = CountryFactory.create()

        # 1 contact whose country is self.country ...
        ContactFactory.create(country=self.country)
        # ... and 2 contacts operating in it (their own country is elsewhere).
        for contact in ContactFactory.create_batch(2, country=other_country):
            contact.countries_of_operation.set([self.country])

        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))

    def test_each_relation_reports_its_own_count(self) -> None:
        response = self.query(
            """
            query { countryList(ordering: "id") { results {
              id
              contacts(pageSize: 10) { totalCount results { id } }
              operatingContacts(pageSize: 10) { totalCount results { id } }
            } } }
            """
        )
        self.assertResponseNoErrors(response)
        results = {row["id"]: row for row in json.loads(response.content)["data"]["countryList"]["results"]}
        node = results[str(self.country.id)]

        self.assertEqual(node["contacts"]["totalCount"], 1)
        self.assertEqual(len(node["contacts"]["results"]), 1)
        self.assertEqual(node["operatingContacts"]["totalCount"], 2)
        self.assertEqual(len(node["operatingContacts"]["results"]), 2)


class TestCountryTotalFigureDisaggregationLoader(HelixGraphQLTestCase):
    """The four current-year totals of a country come from one annotation, so one batch —
    and one query — serves all four, each field keying into the country's own totals.
    """

    DISAGGREGATION_ALIASES = (
        Country.ND_CONFLICT_ANNOTATE,
        Country.ND_DISASTER_ANNOTATE,
        Country.IDP_CONFLICT_ANNOTATE,
        Country.IDP_DISASTER_ANNOTATE,
    )

    @classmethod
    def setUpTestData(cls):
        year = timezone.now().year
        FLOW_END = date(year, 3, 10)
        STOCK_END = date(year, 12, 31)
        cls.conflict_event = EventFactory.create(event_type=Crisis.CRISIS_TYPE.CONFLICT)
        cls.disaster_event = EventFactory.create(event_type=Crisis.CRISIS_TYPE.DISASTER)
        # Every one of the eight totals differs, so a value landing on the wrong field or the
        # wrong country is visible in the payload.
        cls.expected = {
            "first": {"flow_conflict": 11, "flow_disaster": 22, "stock_conflict": 33, "stock_disaster": 44},
            "second": {"flow_conflict": 55, "flow_disaster": 66, "stock_conflict": 77, "stock_disaster": 88},
        }
        cls.countries = {}
        for name, totals in cls.expected.items():
            country = CountryFactory.create()
            cls.countries[name] = country
            for event, category, total, end in (
                # A flow figure counts when it starts inside the year; a stock figure counts
                # when it ends on the year's last day.
                (cls.conflict_event, Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT, totals["flow_conflict"], FLOW_END),
                (cls.disaster_event, Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT, totals["flow_disaster"], FLOW_END),
                (cls.conflict_event, Figure.FIGURE_CATEGORY_TYPES.IDPS, totals["stock_conflict"], STOCK_END),
                (cls.disaster_event, Figure.FIGURE_CATEGORY_TYPES.IDPS, totals["stock_disaster"], STOCK_END),
            ):
                FigureFactory.create(
                    country=country,
                    event=event,
                    category=category,
                    role=Figure.ROLE.RECOMMENDED,
                    total_figures=total,
                    start_date=date(year, 1, 10),
                    end_date=end,
                )

    def setUp(self) -> None:
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))

    def test_four_totals_come_from_one_query(self) -> None:
        query = """
            query { countryList(ordering: "id") { results {
              id totalFlowConflict totalFlowDisaster totalStockConflict totalStockDisaster
            } } }
        """
        with CaptureQueriesContext(connection) as ctx:
            response = self.query(query)
            self.assertResponseNoErrors(response)
        disaggregation_queries = [
            q["sql"] for q in ctx.captured_queries if any(alias in q["sql"] for alias in self.DISAGGREGATION_ALIASES)
        ]
        self.assertEqual(len(disaggregation_queries), 1, disaggregation_queries)

        results = {row["id"]: row for row in json.loads(response.content)["data"]["countryList"]["results"]}
        for name, totals in self.expected.items():
            node = results[str(self.countries[name].id)]
            self.assertEqual(
                (
                    node["totalFlowConflict"],
                    node["totalFlowDisaster"],
                    node["totalStockConflict"],
                    node["totalStockDisaster"],
                ),
                (
                    totals["flow_conflict"],
                    totals["flow_disaster"],
                    totals["stock_conflict"],
                    totals["stock_disaster"],
                ),
                name,
            )

    def test_values_follow_key_order_and_a_missing_key_holds_its_place(self) -> None:
        first, second = self.countries["first"], self.countries["second"]
        missing = first.id + second.id  # no such country
        keys = [second.id, missing, first.id]
        values = CountryTotalFigureDisaggregationLoader().batch_load_fn(keys).get()

        self.assertEqual(
            [value[Country.ND_CONFLICT_ANNOTATE] for value in values],
            [self.expected["second"]["flow_conflict"], None, self.expected["first"]["flow_conflict"]],
        )
        self.assertEqual(
            [value[Country.IDP_DISASTER_ANNOTATE] for value in values],
            [self.expected["second"]["stock_disaster"], None, self.expected["first"]["stock_disaster"]],
        )
        # A key with no row still carries every field, so no reader has to guess.
        self.assertEqual(set(values[1]), set(self.DISAGGREGATION_ALIASES))

    def test_totals_match_the_per_country_subquery(self) -> None:
        # The loader reads the grouped-CTE path; it must report what the correlated
        # subquery reports for the same (default current-year) scope.
        keys = [self.countries["first"].id, self.countries["second"].id]
        loaded = CountryTotalFigureDisaggregationLoader().batch_load_fn(keys).get()
        subquery_rows = {
            row["id"]: {field: row[field] for field in self.DISAGGREGATION_ALIASES}
            for row in Country.objects.filter(id__in=keys)
            .annotate(**Country._total_figure_disaggregation_subquery())
            .values("id", *self.DISAGGREGATION_ALIASES)
        }
        self.assertEqual(loaded, [subquery_rows[key] for key in keys])

    def test_a_country_without_figures_reports_no_totals(self) -> None:
        empty = CountryFactory.create()
        values = CountryTotalFigureDisaggregationLoader().batch_load_fn([empty.id]).get()
        self.assertEqual(values, [{field: None for field in self.DISAGGREGATION_ALIASES}])
