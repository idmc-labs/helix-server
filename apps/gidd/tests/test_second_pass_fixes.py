"""Regression guards for two defects the equivalence gate cannot see.

Both are invisible to a differential check: the geojson value is wrong identically on every ref,
and the null argument is a request shape no spec sends. Only a value-level test catches either.
"""

import json

from django.test import TestCase

from apps.contrib.models import Client
from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.gidd.models import GiddDisplacement, GiddFigure, ReleaseMetadata, StatusLog
from apps.gidd.tasks import update_gidd_data
from apps.gidd.views import DisaggregationViewSet
from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    DisasterCategoryFactory,
    DisasterSubCategoryFactory,
    DisasterSubTypeFactory,
    DisasterTypeFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
    FigureLocationFactory,
    ReportFactory,
    UserFactory,
    ViolenceSubTypeFactory,
)
from utils.tests import HelixGraphQLTestCase, create_user_with_role

RELEASE_YEAR = 2023

CONFLICT_STATISTICS = """
    query($clientId: String!, $releaseEnvironment: String) {
        giddPublicConflictStatistics(clientId: $clientId, releaseEnvironment: $releaseEnvironment) {
            newDisplacements
            totalDisplacements
        }
    }
"""

CONFLICT_BREAKDOWN = """
    query($clientId: String!, $countriesIso3: [String!]) {
        giddPublicConflictStatistics(clientId: $clientId, countriesIso3: $countriesIso3) {
            newDisplacements
            totalDisplacements
            displacementsByViolenceSubType { label newDisplacements totalDisplacements }
        }
    }
"""


class GiddHousingDestructionExportTestCase(TestCase):
    """`is_housing_destruction` must read the same in the geojson as in the xlsx.

    The column is `BooleanField(default=False, null=True)`, so `False` is a common stored value and
    an `is not None` test reports it as "Yes". The two exports are built by separate code paths over
    one row, which is why they can disagree while both look well-formed.
    """

    def setUp(self) -> None:
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.country = CountryFactory(name="Nepal", iso3="NPL")
        self.event = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.DISASTER,
            start_date="2018-01-01",
            end_date="2018-12-31",
            disaster_category=DisasterCategoryFactory.create(),
            disaster_sub_category=DisasterSubCategoryFactory.create(),
            disaster_type=DisasterTypeFactory.create(),
            disaster_sub_type=DisasterSubTypeFactory.create(),
        )
        self.event.countries.add(self.country)

        report = ReportFactory.create(is_gidd_report=True, gidd_report_year=2018)
        self.expected = {}
        for value in (True, False, None):
            figure = FigureFactory.create(
                entry=EntryFactory.create(publish_date="2019-01-01"),
                event=self.event,
                country=self.country,
                role=Figure.ROLE.RECOMMENDED,
                category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                total_figures=500,
                start_date="2018-01-01",
                end_date="2018-12-31",
                is_housing_destruction=value,
            )
            # The geojson emits a feature per figure with geometry; a figure with no location is
            # skipped entirely, so the fixture would render empty and assert nothing.
            figure.geo_locations.add(FigureLocationFactory.create(display_name=f"Zone-{value}"))
            report.figures.add(figure)
            self.expected[figure.id] = "Yes" if value else "No"

        status_log = StatusLog.objects.create(
            triggered_by=self.user,
            triggered_at="2018-01-01",
            completed_at="2018-01-01",
            status=StatusLog.Status.PENDING,
        )
        update_gidd_data(status_log.id)
        status_log.refresh_from_db()
        assert status_log.status == StatusLog.Status.SUCCESS, "generation did not succeed"

    def rendered(self, payload_iter):
        return json.loads(b"".join(payload_iter).decode())["features"]

    def test_false_is_not_published_as_housing_destruction(self):
        features = self.rendered(
            DisaggregationViewSet()._export_disaggregated_geojson("probe.geojson", GiddFigure.objects.all())
        )
        got = {f["properties"]["ID"]: f["properties"].get("Is housing destruction") for f in features}
        assert len(got) == 3, got
        # The defect: `is not None` rendered a stored False as "Yes".
        assert got == self.expected, got


class GiddNullReleaseEnvironmentTestCase(HelixGraphQLTestCase):
    """An explicit null `releaseEnvironment` must fall back to RELEASE, not raise.

    `.get(key, default)` returns None when the key is present carrying null, so the default never
    applies and `.lower()` fails. Because the statistics fields are non-null on the root `Query`,
    that error nulls every sibling field in the document rather than only the one that failed.
    """

    @classmethod
    def setUpTestData(cls):
        cls.client_code = "GIDD-NULL-RELEASE-ENV"
        Client.objects.create(name="Gidd Null Env", code=cls.client_code, is_active=True)
        ReleaseMetadata.objects.create(
            release_year=RELEASE_YEAR,
            pre_release_year=RELEASE_YEAR - 1,
            modified_by=UserFactory.create(),
        )
        country = CountryFactory.create(name="Nepal", iso3="NPL")
        GiddDisplacement.objects.create(
            country=country,
            iso3=country.iso3,
            country_name=country.name,
            year=RELEASE_YEAR,
            cause=Crisis.CRISIS_TYPE.CONFLICT,
            new_displacement=500,
            total_displacement=5000,
        )

    def statistics(self, **variables):
        response = self.query(
            CONFLICT_STATISTICS,
            variables=dict(clientId=self.client_code, **variables),
        )
        return response.json()

    def test_null_release_environment_is_treated_as_release(self):
        payload = self.statistics(releaseEnvironment=None)
        assert not payload.get("errors"), payload.get("errors")
        assert payload["data"]["giddPublicConflictStatistics"] == self.statistics()["data"]["giddPublicConflictStatistics"]

    def test_release_year_row_is_published_under_the_null_default(self):
        # Non-vacuity: a fallback to PRE_RELEASE would drop the release-year row and pass the
        # equality above only because both sides were empty.
        stats = self.statistics(releaseEnvironment=None)["data"]["giddPublicConflictStatistics"]
        assert stats["newDisplacements"] == 500, stats


class GiddStockOnlyBreakdownTestCase(HelixGraphQLTestCase):
    """A typology with IDP stock and no new displacement must survive into the breakdown.

    The breakdown and the headline read the same rows, so a predicate that admits fewer rows than
    the headline makes the two disagree -- and protracted displacement, a standing IDP population
    with no movement in the year, is exactly the shape that falls through.
    """

    @classmethod
    def setUpTestData(cls):
        cls.client_code = "GIDD-STOCK-ONLY-BREAKDOWN"
        Client.objects.create(name="Gidd Stock Only", code=cls.client_code, is_active=True)
        ReleaseMetadata.objects.create(
            release_year=RELEASE_YEAR,
            pre_release_year=RELEASE_YEAR - 1,
            modified_by=UserFactory.create(),
        )
        country = CountryFactory.create(name="Protractia", iso3="PRO")
        violence_sub_type = ViolenceSubTypeFactory.create(name="IAC")
        GiddDisplacement.objects.create(
            country=country,
            iso3=country.iso3,
            country_name=country.name,
            year=RELEASE_YEAR,
            cause=Crisis.CRISIS_TYPE.CONFLICT,
            violence_sub_type=violence_sub_type,
            violence_sub_type_name=violence_sub_type.name,
            new_displacement=0,
            total_displacement=246901,
        )

    def statistics(self):
        response = self.query(
            CONFLICT_BREAKDOWN,
            variables=dict(clientId=self.client_code, countriesIso3=["PRO"]),
        )
        self.assertResponseNoErrors(response)
        return response.json()["data"]["giddPublicConflictStatistics"]

    def test_the_breakdown_accounts_for_every_idp_the_headline_publishes(self):
        stats = self.statistics()
        assert stats["totalDisplacements"] == 246901, stats
        # The defect: filtering on new displacement alone left the headline standing beside an
        # empty breakdown.
        assert len(stats["displacementsByViolenceSubType"]) == 1, stats
        row = stats["displacementsByViolenceSubType"][0]
        assert row["label"] == "IAC", row
        assert row["totalDisplacements"] == stats["totalDisplacements"], (row, stats)
        assert row["newDisplacements"] == 0, row
