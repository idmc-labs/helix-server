from apps.contrib.models import Client
from apps.crisis.models import Crisis
from apps.gidd.models import GiddDisplacement, GiddEventDisplacement, ReleaseMetadata
from utils.factories import (
    CountryFactory,
    DisasterCategoryFactory,
    DisasterSubCategoryFactory,
    DisasterSubTypeFactory,
    DisasterTypeFactory,
    UserFactory,
)
from utils.tests import HelixGraphQLTestCase

CONFLICT_STATISTICS = """
    query($clientId: String!, $startYear: Float, $endYear: Float) {
        giddPublicConflictStatistics(clientId: $clientId, startYear: $startYear, endYear: $endYear) {
            newDisplacements
            totalDisplacements
            internalDisplacementCountries
            totalDisplacementCountries
            newDisplacementTimeseriesByYear { year total }
            newDisplacementTimeseriesByCountry { year total country { iso3 } }
        }
    }
"""

DISASTER_STATISTICS = """
    query($clientId: String!, $hazardTypes: [ID!], $startYear: Float, $endYear: Float) {
        giddPublicDisasterStatistics(
            clientId: $clientId, hazardTypes: $hazardTypes, startYear: $startYear, endYear: $endYear
        ) {
            newDisplacements
            totalDisplacements
            totalEvents
            displacementsByHazardType { id label newDisplacements }
        }
    }
"""

COMBINED_STATISTICS = """
    query($clientId: String!, $hazardTypes: [ID!]) {
        giddPublicCombinedStatistics(clientId: $clientId, hazardTypes: $hazardTypes) {
            internalDisplacements
            totalDisplacements
            internalDisplacementCountries
            totalDisplacementCountries
        }
    }
"""

DISASTERS_BY_EVENT_NAME = """
    query($clientId: String!, $eventName: String) {
        giddPublicDisplacementEvents(clientId: $clientId, filters: { eventName: $eventName, cause: DISASTER }) {
            totalCount
            results { eventName }
        }
    }
"""


class TestGiddPublicStatistics(HelixGraphQLTestCase):
    """Value-level guards for the public GIDD statistics resolvers: seeded snapshot
    rows with hand-computed expectations, including the release-year gate and the
    IDPs-at-end-year vs NDs-in-range year semantics."""

    @classmethod
    def setUpTestData(cls):
        cls.client_code = "GIDD-STATS-TEST"
        Client.objects.create(name="Gidd Stats", code=cls.client_code, is_active=True)
        ReleaseMetadata.objects.create(release_year=2023, pre_release_year=2022, modified_by=UserFactory.create())

        npl = CountryFactory.create(name="Nepal", iso3="NPL")
        ind = CountryFactory.create(name="India", iso3="IND")

        hazard_sub_category = DisasterSubCategoryFactory.create(category=DisasterCategoryFactory.create())
        cls.flood = DisasterTypeFactory.create(name="Flood")
        cls.storm = DisasterTypeFactory.create(name="Storm")

        def create_conflict(country, year, nd, idps):
            return GiddDisplacement(
                country=country,
                iso3=country.iso3,
                country_name=country.name,
                year=year,
                cause=Crisis.CRISIS_TYPE.CONFLICT,
                new_displacement=nd,
                total_displacement=idps,
            )

        hazard_sub_types = {hazard.id: DisasterSubTypeFactory.create(type=hazard) for hazard in (cls.flood, cls.storm)}

        def hazard_columns(hazard):
            return dict(
                hazard_category=hazard_sub_category.category,
                hazard_sub_category=hazard_sub_category,
                hazard_type=hazard,
                hazard_type_name=hazard.name,
                hazard_sub_type=hazard_sub_types[hazard.id],
            )

        event_ids = {}

        def create_disaster(country, year, hazard, event_name, nd, idps):
            """The rollup row the statistics aggregate, plus its event-level row.

            Generation writes both grains, so a fixture that seeded only one would let a resolver
            reading the wrong table pass. One id per event name, since `totalEvents` counts events
            and generation gives every row of one event the same `event_raw_id`.
            """
            common = dict(
                country=country,
                iso3=country.iso3,
                country_name=country.name,
                year=year,
                cause=Crisis.CRISIS_TYPE.DISASTER,
                new_displacement=nd,
                total_displacement=idps,
                **hazard_columns(hazard),
            )
            event_id = event_ids.setdefault(event_name, len(event_ids) + 1)
            GiddEventDisplacement.objects.create(event_name=event_name, event_raw_id=event_id, **common)
            return GiddDisplacement(**common)

        GiddDisplacement.objects.bulk_create(
            [
                create_conflict(npl, 2021, 50, 500),
                create_conflict(npl, 2022, 100, 1000),
                create_conflict(npl, 2023, 200, 2000),
                create_conflict(ind, 2023, 400, 4000),
                # Beyond release_year 2023: the release must exclude it.
                create_conflict(npl, 2024, 999_999, 999_999),
            ]
        )

        GiddDisplacement.objects.bulk_create(
            [
                create_disaster(npl, 2023, cls.flood, "Karnali Flood", 10, 100),
                create_disaster(npl, 2022, cls.storm, "Bagmati Storm", 20, 200),
                create_disaster(ind, 2023, cls.flood, "Ganges Flood", 40, 400),
                # Beyond release_year 2023: the release must exclude it.
                create_disaster(npl, 2024, cls.flood, "Future Flood", 88_888, 88_888),
            ]
        )

    def stats(self, document, **variables):
        response = self.query(document, variables=dict(clientId=self.client_code, **variables))
        self.assertResponseNoErrors(response)
        return next(iter(response.json()["data"].values()))

    def test_conflict_statistics(self):
        data = self.stats(CONFLICT_STATISTICS)
        self.assertEqual(data["newDisplacements"], 50 + 100 + 200 + 400)
        # IDPs are a stock: without an endYear the snapshot defaults to the
        # release year (2023) — never a sum across yearly snapshots.
        self.assertEqual(data["totalDisplacements"], 2000 + 4000)
        self.assertEqual(data["internalDisplacementCountries"], 2)
        self.assertEqual(data["totalDisplacementCountries"], 2)
        # The by-year series is derived from the by-country rows: both must agree.
        self.assertEqual(
            data["newDisplacementTimeseriesByYear"],
            [dict(year=2021, total=50), dict(year=2022, total=100), dict(year=2023, total=600)],
        )
        self.assertEqual(
            sorted(
                (row["year"], row["country"]["iso3"], row["total"]) for row in data["newDisplacementTimeseriesByCountry"]
            ),
            [(2021, "NPL", 50), (2022, "NPL", 100), (2023, "IND", 400), (2023, "NPL", 200)],
        )

    def test_conflict_statistics_with_year_range(self):
        data = self.stats(CONFLICT_STATISTICS, startYear=2022, endYear=2023)
        # NDs accumulate over the range; IDPs are the end-year snapshot.
        self.assertEqual(data["newDisplacements"], 100 + 200 + 400)
        self.assertEqual(data["totalDisplacements"], 2000 + 4000)

    def test_disaster_statistics(self):
        data = self.stats(DISASTER_STATISTICS)
        self.assertEqual(data["newDisplacements"], 10 + 20 + 40)
        self.assertEqual(data["totalDisplacements"], 100 + 400)  # 2023 snapshot
        self.assertEqual(data["totalEvents"], 3)
        by_hazard = {row["label"]: row["newDisplacements"] for row in data["displacementsByHazardType"]}
        self.assertEqual(by_hazard, {"Flood": 10 + 40, "Storm": 20})

    def test_disaster_statistics_with_hazard_type(self):
        data = self.stats(DISASTER_STATISTICS, hazardTypes=[str(self.flood.id)])
        self.assertEqual(data["newDisplacements"], 10 + 40)
        self.assertEqual(data["totalDisplacements"], 100 + 400)

    def test_combined_statistics(self):
        data = self.stats(COMBINED_STATISTICS)
        self.assertEqual(data["internalDisplacements"], 750 + 70)
        self.assertEqual(data["totalDisplacements"], (2000 + 4000) + (100 + 400))
        self.assertEqual(data["internalDisplacementCountries"], 2)
        self.assertEqual(data["totalDisplacementCountries"], 2)

    def test_combined_statistics_with_hazard_type(self):
        # hazardTypes must filter ONLY the disaster half; the conflict filterset
        # has no such filter and must ignore it.
        data = self.stats(COMBINED_STATISTICS, hazardTypes=[str(self.flood.id)])
        self.assertEqual(data["internalDisplacements"], 750 + 50)
        self.assertEqual(data["totalDisplacements"], (2000 + 4000) + (100 + 400))

    def test_year_filter_invariant(self):
        # `no year filter` and `startYear=<before all data>, endYear=<release year>`
        # must return byte-identical statistics.
        unfiltered = self.stats(CONFLICT_STATISTICS)
        explicit = self.stats(CONFLICT_STATISTICS, startYear=1990, endYear=2023)
        self.assertEqual(unfiltered, explicit)

    def test_disasters_filtered_by_event_name(self):
        data = self.stats(DISASTERS_BY_EVENT_NAME, eventName="karnali")
        self.assertEqual(data["totalCount"], 1)
        self.assertEqual(data["results"][0]["eventName"], "Karnali Flood")

    def test_end_year_beyond_the_release_year_is_refused(self):
        # Rows stop at the release year, so a later endYear used to return the full new
        # displacement figure beside a zero stock rather than saying the year is out of range.
        response = self.query(
            CONFLICT_STATISTICS,
            variables=dict(clientId=self.client_code, endYear=2050),
        )
        errors = response.json().get("errors") or []
        self.assertTrue(errors, "endYear past the release year was accepted")
        self.assertIn("endYear cannot be greater than the release year", errors[0]["message"])

    def test_end_year_at_the_release_year_is_accepted(self):
        data = self.stats(CONFLICT_STATISTICS, endYear=2023)
        self.assertEqual(data["totalDisplacements"], 2000 + 4000)


class TestGiddPublicDisasterTotalEvents(HelixGraphQLTestCase):
    """`totalEvents` counts events, not the rows that carry them.

    A row is per (event, country, year), so one event reaching two countries over two years
    occupies four of them.
    """

    @classmethod
    def setUpTestData(cls):
        cls.client_code = "GIDD-EVENT-COUNT-TEST"
        Client.objects.create(name="Gidd Event Count", code=cls.client_code, is_active=True)
        ReleaseMetadata.objects.create(release_year=2023, pre_release_year=2022, modified_by=UserFactory.create())

        hazard = DisasterTypeFactory.create(name="Flood")
        sub_category = DisasterSubCategoryFactory.create(category=DisasterCategoryFactory.create())
        countries = [CountryFactory.create(name=name, iso3=iso3) for name, iso3 in (("Nepal", "NPL"), ("India", "IND"))]

        def row(country, year, event_raw_id, event_name):
            GiddEventDisplacement.objects.create(
                country=country,
                iso3=country.iso3,
                country_name=country.name,
                year=year,
                cause=Crisis.CRISIS_TYPE.DISASTER,
                event_raw_id=event_raw_id,
                event_name=event_name,
                new_displacement=1,
                total_displacement=1,
                hazard_category=sub_category.category,
                hazard_sub_category=sub_category,
                hazard_type=hazard,
                hazard_type_name=hazard.name,
                hazard_sub_type=DisasterSubTypeFactory.create(type=hazard),
            )

        cls.rows = 0
        for country in countries:
            for year in (2022, 2023):
                row(country, year, 1, "Basin Flood")
                cls.rows += 1
        row(countries[0], 2023, 2, "Other Flood")
        cls.rows += 1

    def test_one_event_across_countries_and_years_counts_once(self):
        response = self.query(DISASTER_STATISTICS, variables=dict(clientId=self.client_code, startYear=2022, endYear=2023))
        self.assertResponseNoErrors(response)
        data = response.json()["data"]["giddPublicDisasterStatistics"]
        self.assertEqual(self.rows, 5)
        self.assertEqual(data["totalEvents"], 2)
