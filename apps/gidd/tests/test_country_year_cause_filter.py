"""`cause` on the country-year displacement list, and why the count needs it.

`giddPublicCountryYearDisplacements` aggregates `GiddDisplacement` to one row per country x year
and keeps a row when any of its four figure columns is above zero. A caller wanting one cause can
hide the other cause's columns, but the rows themselves still arrive: a country-year carrying only
conflict figures comes back with both disaster cells empty, and `totalCount` -- what a pager reads
-- still counts it. Paging then walks pages that render blank.

Scoping to a cause drops the other cause's rows before the aggregation runs, so those country-years
fail the row filter and leave both `results` and `totalCount`. That is the part column hiding cannot
reach, and it is what these tests pin.
"""

from apps.contrib.models import Client
from apps.crisis.models import Crisis
from apps.gidd.models import GiddDisplacement, ReleaseMetadata
from utils.factories import CountryFactory, UserFactory
from utils.tests import HelixGraphQLTestCase

COUNTRY_YEAR_DISPLACEMENTS = """
    query($clientId: String!, $cause: CRISIS_TYPE) {
        giddPublicCountryYearDisplacements(clientId: $clientId, cause: $cause) {
            totalCount
            results {
                iso3
                year
                conflictNewDisplacement
                conflictTotalDisplacement
                disasterNewDisplacement
                disasterTotalDisplacement
            }
        }
    }
"""

RELEASE_YEAR = 2023


class TestGiddCountryYearCauseFilter(HelixGraphQLTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client_code = "GIDD-COUNTRY-YEAR-CAUSE"
        Client.objects.create(name="Gidd Country Year", code=cls.client_code, is_active=True)
        ReleaseMetadata.objects.create(
            release_year=RELEASE_YEAR,
            pre_release_year=RELEASE_YEAR - 1,
            modified_by=UserFactory.create(),
        )

        npl = CountryFactory.create(name="Nepal", iso3="NPL")
        ind = CountryFactory.create(name="India", iso3="IND")

        def row(country, year, cause, nd, idps):
            return GiddDisplacement(
                country=country,
                iso3=country.iso3,
                country_name=country.name,
                year=year,
                cause=cause,
                new_displacement=nd,
                total_displacement=idps,
            )

        conflict = Crisis.CRISIS_TYPE.CONFLICT
        disaster = Crisis.CRISIS_TYPE.DISASTER

        GiddDisplacement.objects.bulk_create(
            [
                # NPL 2023 carries both causes, so it survives either scoping.
                row(npl, RELEASE_YEAR, conflict, 200, 2000),
                row(npl, RELEASE_YEAR, disaster, 10, 100),
                # IND 2023 is conflict-only: a disaster-scoped list must not return it.
                row(ind, RELEASE_YEAR, conflict, 400, 4000),
                # NPL 2022 is disaster-only: a conflict-scoped list must not return it.
                row(npl, RELEASE_YEAR - 1, disaster, 20, 200),
            ]
        )

    def rows(self, **variables):
        response = self.query(
            COUNTRY_YEAR_DISPLACEMENTS,
            variables=dict(clientId=self.client_code, **variables),
        )
        self.assertResponseNoErrors(response)
        return response.json()["data"]["giddPublicCountryYearDisplacements"]

    def test_unscoped_returns_every_country_year(self):
        data = self.rows()
        self.assertEqual(data["totalCount"], 3)
        self.assertEqual(
            {(row["iso3"], row["year"]) for row in data["results"]},
            {("NPL", RELEASE_YEAR), ("IND", RELEASE_YEAR), ("NPL", RELEASE_YEAR - 1)},
        )

    def test_cause_drops_the_other_cause_from_results_and_count(self):
        data = self.rows(cause="DISASTER")
        # IND 2023 is conflict-only and must be gone entirely -- not present with empty cells.
        self.assertEqual(data["totalCount"], 2)
        self.assertEqual(
            {(row["iso3"], row["year"]) for row in data["results"]},
            {("NPL", RELEASE_YEAR), ("NPL", RELEASE_YEAR - 1)},
        )

        data = self.rows(cause="CONFLICT")
        self.assertEqual(data["totalCount"], 2)
        self.assertEqual(
            {(row["iso3"], row["year"]) for row in data["results"]},
            {("NPL", RELEASE_YEAR), ("IND", RELEASE_YEAR)},
        )

    def test_cause_zeroes_the_excluded_cause_on_a_surviving_row(self):
        # NPL 2023 has both causes, so scoping keeps the row but must not let the
        # excluded cause's figures through the aggregate.
        npl = next(
            row for row in self.rows(cause="DISASTER")["results"] if row["iso3"] == "NPL" and row["year"] == RELEASE_YEAR
        )
        self.assertEqual(npl["disasterNewDisplacement"], 10)
        self.assertEqual(npl["disasterTotalDisplacement"], 100)
        self.assertIsNone(npl["conflictNewDisplacement"])
        self.assertIsNone(npl["conflictTotalDisplacement"])

    def test_unknown_cause_is_refused_rather_than_ignored(self):
        # A ChoiceFilter would drop the failed field from `cleaned_data` and quietly
        # return every row; the enum input makes it an error instead.
        response = self.query(
            COUNTRY_YEAR_DISPLACEMENTS,
            variables=dict(clientId=self.client_code, cause="NOT_A_CAUSE"),
        )
        self.assertTrue(response.json().get("errors"))
