"""
Contract tests for the public GIDD REST endpoints (`/external-api/gidd/...`).

These endpoints are consumed by external systems, so the serialized key set, the
key ORDER and the serialized values are a public contract. They are pinned here
so any change to `Meta.fields`, to a serializer field class, or to the way rows
are projected shows up as a test failure.
"""

import datetime
from unittest.mock import patch

from apps.contrib.redis_client_track import create_client_track_cache_key
from apps.crisis.models import Crisis
from apps.entry.models import ExternalApiDump, Figure
from apps.event.models import EventCode
from apps.gidd.models import (
    GiddDisplacement,
    GiddEventDisplacement,
    PublicFigureAnalysis,
    ReleaseMetadata,
    StatusLog,
)
from apps.gidd.views import (
    ConflictViewSet,
    CountryViewSet,
    DisasterViewSet,
    DisplacementDataViewSet,
    PublicFigureAnalysisViewSet,
)
from helix.caches import external_api_cache
from utils.common import round_and_remove_zero
from utils.factories import (
    ClientFactory,
    CountryFactory,
    DisasterCategoryFactory,
    DisasterSubCategoryFactory,
    DisasterSubTypeFactory,
    DisasterTypeFactory,
    EventCodeFactory,
    EventFactory,
)
from utils.tests import HelixAPITestCase

COUNTRIES_URL = "/external-api/gidd/countries/"
CONFLICTS_URL = "/external-api/gidd/conflicts/"
DISASTERS_URL = "/external-api/gidd/disasters/"
DISPLACEMENTS_URL = "/external-api/gidd/displacements/"
PFA_URL = "/external-api/gidd/public-figure-analyses/"

# The paginated envelope produced by GiddLimitOffsetPagination. `last_updated`
# is appended LAST: the pagination class only calls `move_to_end` when the
# response data is an OrderedDict, and DRF 3.15 builds it as a plain dict, so
# the reordering never happens (the OpenAPI schema override, which advertises
# `last_updated` first, therefore disagrees with the wire format).
ENVELOPE_KEYS = ["count", "next", "previous", "results", "last_updated"]

COUNTRY_FIELDS = [
    "iso2",
    "iso3",
    "country_name",
]

CONFLICT_FIELDS = [
    "iso3",
    "country_name",
    "year",
    "new_displacement",
    "new_displacement_rounded",
    "total_displacement_rounded",
    "total_displacement",
]

DISASTER_FIELDS = [
    "iso3",
    "country_name",
    "year",
    "start_date",
    "start_date_accuracy",
    "end_date",
    "end_date_accuracy",
    "event_name",
    "new_displacement",
    "new_displacement_rounded",
    "total_displacement",
    "total_displacement_rounded",
    "hazard_category",
    "hazard_category_name",
    "hazard_sub_category",
    "hazard_sub_category_name",
    "hazard_type",
    "hazard_type_name",
    "hazard_sub_type",
    "hazard_sub_type_name",
    "event_codes",
    "event_codes_type",
]

DISPLACEMENT_FIELDS = [
    "iso3",
    "country_name",
    "year",
    "conflict_new_displacement",
    "conflict_new_displacement_rounded",
    "conflict_total_displacement",
    "conflict_total_displacement_rounded",
    "disaster_new_displacement",
    "disaster_new_displacement_rounded",
    "disaster_total_displacement",
    "disaster_total_displacement_rounded",
]

# NOTE: `figure_category` is listed twice in PublicFigureAnalysisSerializer.Meta.fields;
# DRF de-duplicates it, keeping the first position.
PFA_FIELDS = [
    "iso3",
    "year",
    "figure_cause",
    "figure_cause_name",
    "figure_category",
    "figure_category_name",
    "description",
    "figures",
    "figures_rounded",
]

RELEASE_YEAR = 2024
DATA_YEAR = 2020
LAST_RELEASE_DATE = datetime.datetime(2024, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)


class GiddRestApiMixin:
    """Fixtures shared by every endpoint test: a registered client, release
    metadata (the list filtersets refuse to run without it), a completed status
    log (drives `last_updated`) and two countries."""

    CLIENT_CODE = "gidd-rest-client"

    def setUp(self):
        super().setUp()
        self.gidd_client = ClientFactory.create(code=self.CLIENT_CODE, is_active=True)
        external_api_cache.set("client_ids", [self.CLIENT_CODE], None)

        ReleaseMetadata.objects.create(
            release_year=RELEASE_YEAR,
            pre_release_year=RELEASE_YEAR - 1,
            modified_by=self.user,
        )
        status_log = StatusLog.objects.create(
            triggered_by=self.user,
            status=StatusLog.Status.SUCCESS,
        )
        StatusLog.objects.filter(pk=status_log.pk).update(completed_at=LAST_RELEASE_DATE)

        self.country_afg = CountryFactory.create(iso3="AFG", iso2="AF", idmc_short_name="Afghanistan")
        # iso2 is nullable: pins how a NULL char field is serialized.
        self.country_npl = CountryFactory.create(iso3="NPL", iso2=None, idmc_short_name="Nepal")

    def tearDown(self):
        external_api_cache.delete("client_ids")
        super().tearDown()

    def get_list(self, url, **params):
        query = {"client_id": self.CLIENT_CODE, **params}
        response = self.client.get(url, query)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def by_iso3(self, payload):
        return {row["iso3"]: row for row in payload["results"]}

    def assert_envelope(self, payload, count):
        self.assertEqual(list(payload.keys()), ENVELOPE_KEYS)
        self.assertEqual(payload["last_updated"], "2024-05-13")
        self.assertEqual(payload["count"], count)
        self.assertIsNone(payload["next"])
        self.assertIsNone(payload["previous"])


class TestGiddCountryRestApi(GiddRestApiMixin, HelixAPITestCase):
    def test_contract_and_values(self):
        payload = self.get_list(COUNTRIES_URL)
        self.assert_envelope(payload, 2)
        self.assertEqual(list(payload["results"][0].keys()), COUNTRY_FIELDS)

        rows = self.by_iso3(payload)
        # `country_name` is `source="idmc_short_name"`.
        self.assertEqual(rows["AFG"], {"iso2": "AF", "iso3": "AFG", "country_name": "Afghanistan"})
        self.assertEqual(rows["NPL"], {"iso2": None, "iso3": "NPL", "country_name": "Nepal"})

    def test_list_query_count(self):
        # client lookup + COUNT + page + StatusLog.last_release_date
        with self.assertNumQueries(4):
            self.client.get(COUNTRIES_URL, {"client_id": self.CLIENT_CODE})


class TestGiddConflictRestApi(GiddRestApiMixin, HelixAPITestCase):
    def setUp(self):
        super().setUp()
        # The endpoint recomputes the rounded figures from the summed raw values, so the stored
        # `*_rounded` columns are never read: they are seeded wrong to prove it.
        GiddDisplacement.objects.create(
            country=self.country_afg,
            iso3="AFG",
            country_name="Afghanistan",
            year=DATA_YEAR,
            cause=Crisis.CRISIS_TYPE.CONFLICT,
            new_displacement=12345,
            new_displacement_rounded=999,
            total_displacement=54321,
            total_displacement_rounded=999,
        )
        # Every displacement figure NULL: rows are not filtered out by the
        # conflict filterset, so the NULLs must survive serialization.
        GiddDisplacement.objects.create(
            country=self.country_npl,
            iso3="NPL",
            country_name="Nepal",
            year=DATA_YEAR,
            cause=Crisis.CRISIS_TYPE.CONFLICT,
            new_displacement=None,
            new_displacement_rounded=None,
            total_displacement=None,
            total_displacement_rounded=None,
        )

    def test_contract_and_values(self):
        payload = self.get_list(CONFLICTS_URL)
        self.assert_envelope(payload, 2)
        self.assertEqual(list(payload["results"][0].keys()), CONFLICT_FIELDS)

        rows = self.by_iso3(payload)
        self.assertEqual(
            rows["AFG"],
            {
                "iso3": "AFG",
                "country_name": "Afghanistan",
                "year": DATA_YEAR,
                "new_displacement": 12345,
                "new_displacement_rounded": round_and_remove_zero(12345),
                "total_displacement_rounded": round_and_remove_zero(54321),
                "total_displacement": 54321,
            },
        )
        self.assertEqual(
            rows["NPL"],
            {
                "iso3": "NPL",
                "country_name": "Nepal",
                "year": DATA_YEAR,
                "new_displacement": None,
                "new_displacement_rounded": None,
                "total_displacement_rounded": None,
                "total_displacement": None,
            },
        )

    def test_release_environment_filter_drops_future_years(self):
        GiddDisplacement.objects.create(
            country=self.country_afg,
            iso3="AFG",
            country_name="Afghanistan",
            year=RELEASE_YEAR + 1,
            cause=Crisis.CRISIS_TYPE.CONFLICT,
            new_displacement=1,
        )
        self.assertEqual(self.get_list(CONFLICTS_URL)["count"], 2)

    def test_list_query_count(self):
        # client lookup + ReleaseMetadata + COUNT + page + StatusLog.last_release_date
        with self.assertNumQueries(5):
            self.client.get(CONFLICTS_URL, {"client_id": self.CLIENT_CODE})


class TestGiddDisasterRestApi(GiddRestApiMixin, HelixAPITestCase):
    def setUp(self):
        super().setUp()
        self.hazard_category = DisasterCategoryFactory.create(name="Natural")
        self.hazard_sub_category = DisasterSubCategoryFactory.create(name="Geophysical", category=self.hazard_category)
        self.hazard_type = DisasterTypeFactory.create(name="Earthquake", disaster_sub_category=self.hazard_sub_category)
        self.hazard_sub_type = DisasterSubTypeFactory.create(name="Ground shaking", type=self.hazard_type)

        # The event table holds both causes, so every disaster row must say so: the endpoint
        # filters on it, and the column is NOT NULL.
        self.hazard_kwargs = dict(
            cause=Crisis.CRISIS_TYPE.DISASTER,
            hazard_category=self.hazard_category,
            hazard_sub_category=self.hazard_sub_category,
            hazard_type=self.hazard_type,
            hazard_sub_type=self.hazard_sub_type,
        )

        # The dump publishes the stored `all_country_event_codes` columns, frozen at generation
        # time. The `EventCode` rows below carry DIFFERENT codes from those columns, so an endpoint
        # that derived them live would fail here -- that is the release-snapshot property.
        self.event = EventFactory.create(
            name="Afghanistan: Earthquake - Herat - June 2020",
            event_type=Crisis.CRISIS_TYPE.DISASTER,
        )
        for code, code_type in (
            ("LIVE-EDIT-1", EventCode.EVENT_CODE_TYPE.GLIDE_NUMBER),
            ("LIVE-EDIT-2", EventCode.EVENT_CODE_TYPE.GOV_ASSIGNED_IDENTIFIER),
        ):
            EventCodeFactory.create(event=self.event, country=self.country_afg, event_code=code, event_code_type=code_type)

        GiddEventDisplacement.objects.create(
            event=self.event,
            event_raw_id=self.event.id,
            country=self.country_afg,
            iso3="AFG",
            country_name="Afghanistan",
            year=DATA_YEAR,
            event_name="Afghanistan: Earthquake - Herat - June 2020",
            start_date=datetime.date(2020, 6, 1),
            start_date_accuracy="Day",
            end_date=datetime.date(2020, 6, 30),
            end_date_accuracy="Month",
            new_displacement=12345,
            new_displacement_rounded=12000,
            total_displacement=54321,
            total_displacement_rounded=54000,
            hazard_category_name="Natural",
            hazard_sub_category_name="Geophysical",
            hazard_type_name="Earthquake",
            hazard_sub_type_name="Ground shaking",
            # The per-country columns hold different values from the all-country ones, so the
            # assertion below can only pass if the serializer reads `all_country_event_codes*`.
            event_codes=["PER-COUNTRY-1"],
            event_codes_type=["Government Assigned Identifier"],
            all_country_event_codes=["GLIDE-1", "GLIDE-2"],
            all_country_event_codes_type=["Glide Number", "Government Assigned Identifier"],
            displacement_occurred=[Figure.DISPLACEMENT_OCCURRED.BEFORE.value],
            **self.hazard_kwargs,
        )
        # Awkward row: NULL dates, NULL accuracies, empty array fields, NULL
        # `new_displacement` (kept in the list only because total_displacement > 0),
        # blank cached hazard names.
        GiddEventDisplacement.objects.create(
            country=self.country_npl,
            iso3="NPL",
            country_name="Nepal",
            year=DATA_YEAR,
            event_name="Nepal: Flood",
            start_date=None,
            start_date_accuracy=None,
            end_date=None,
            end_date_accuracy=None,
            new_displacement=None,
            new_displacement_rounded=None,
            total_displacement=7,
            total_displacement_rounded=None,
            hazard_category_name="",
            hazard_sub_category_name="",
            hazard_type_name="",
            hazard_sub_type_name="",
            event_codes=[],
            event_codes_type=[],
            **self.hazard_kwargs,
        )

    def test_contract_and_values(self):
        payload = self.get_list(DISASTERS_URL)
        self.assert_envelope(payload, 2)
        self.assertEqual(list(payload["results"][0].keys()), DISASTER_FIELDS)

        rows = self.by_iso3(payload)
        self.assertEqual(
            rows["AFG"],
            {
                "iso3": "AFG",
                "country_name": "Afghanistan",
                "year": DATA_YEAR,
                "start_date": "2020-06-01",
                "start_date_accuracy": "Day",
                "end_date": "2020-06-30",
                "end_date_accuracy": "Month",
                "event_name": "Afghanistan: Earthquake - Herat - June 2020",
                "new_displacement": 12345,
                "new_displacement_rounded": 12000,
                "total_displacement": 54321,
                "total_displacement_rounded": 54000,
                # hazard_* are PrimaryKeyRelatedField: the raw pk, not the label.
                "hazard_category": self.hazard_category.pk,
                "hazard_category_name": "Natural",
                "hazard_sub_category": self.hazard_sub_category.pk,
                "hazard_sub_category_name": "Geophysical",
                "hazard_type": self.hazard_type.pk,
                "hazard_type_name": "Earthquake",
                "hazard_sub_type": self.hazard_sub_type.pk,
                "hazard_sub_type_name": "Ground shaking",
                "event_codes": ["GLIDE-1", "GLIDE-2"],
                "event_codes_type": ["Glide Number", "Government Assigned Identifier"],
            },
        )
        self.assertEqual(
            rows["NPL"],
            {
                "iso3": "NPL",
                "country_name": "Nepal",
                "year": DATA_YEAR,
                "start_date": None,
                "start_date_accuracy": None,
                "end_date": None,
                "end_date_accuracy": None,
                "event_name": "Nepal: Flood",
                "new_displacement": None,
                "new_displacement_rounded": None,
                "total_displacement": 7,
                "total_displacement_rounded": None,
                "hazard_category": self.hazard_category.pk,
                "hazard_category_name": "",
                "hazard_sub_category": self.hazard_sub_category.pk,
                "hazard_sub_category_name": "",
                "hazard_type": self.hazard_type.pk,
                "hazard_type_name": "",
                "hazard_sub_type": self.hazard_sub_type.pk,
                "hazard_sub_type_name": "",
                "event_codes": [],
                "event_codes_type": [],
            },
        )

    def test_rows_without_any_displacement_are_excluded(self):
        # RestDisasterFilterSet keeps only rows reporting new OR total displacement.
        GiddEventDisplacement.objects.create(
            country=self.country_afg,
            iso3="AFG",
            country_name="Afghanistan",
            year=DATA_YEAR,
            event_name="Afghanistan: no displacement",
            new_displacement=None,
            total_displacement=None,
            **self.hazard_kwargs,
        )
        payload = self.get_list(DISASTERS_URL)
        self.assertEqual(payload["count"], 2)
        self.assertNotIn("Afghanistan: no displacement", [row["event_name"] for row in payload["results"]])

    def test_list_query_count(self):
        # client lookup + ReleaseMetadata + COUNT + page + StatusLog.last_release_date
        with self.assertNumQueries(5):
            self.client.get(DISASTERS_URL, {"client_id": self.CLIENT_CODE})


class TestGiddDisplacementDataRestApi(GiddRestApiMixin, HelixAPITestCase):
    def setUp(self):
        super().setUp()

        # The endpoint conditional-sums the cause-tagged rollup, so the split it publishes needs
        # one row per cause. A cause with no row at all must still serialize as NULL, not 0.
        def seed(country, cause, nd, idps):
            GiddDisplacement.objects.create(
                country=country,
                iso3=country.iso3,
                country_name=country.idmc_short_name,
                year=DATA_YEAR,
                cause=cause,
                new_displacement=nd,
                total_displacement=idps,
            )

        seed(self.country_afg, Crisis.CRISIS_TYPE.CONFLICT, 11, 2222)
        seed(self.country_afg, Crisis.CRISIS_TYPE.DISASTER, 33333, 444444)
        # Only one non-NULL figure, so the row survives the filterset while every other field
        # exercises the NULL path -- and NPL has no disaster row at all.
        seed(self.country_npl, Crisis.CRISIS_TYPE.CONFLICT, None, 9)

    def test_contract_and_values(self):
        payload = self.get_list(DISPLACEMENTS_URL)
        self.assert_envelope(payload, 2)
        self.assertEqual(list(payload["results"][0].keys()), DISPLACEMENT_FIELDS)

        rows = self.by_iso3(payload)
        self.assertEqual(
            rows["AFG"],
            {
                "iso3": "AFG",
                "country_name": "Afghanistan",
                "year": DATA_YEAR,
                "conflict_new_displacement": 11,
                "conflict_new_displacement_rounded": round_and_remove_zero(11),
                "conflict_total_displacement": 2222,
                "conflict_total_displacement_rounded": round_and_remove_zero(2222),
                "disaster_new_displacement": 33333,
                "disaster_new_displacement_rounded": round_and_remove_zero(33333),
                "disaster_total_displacement": 444444,
                "disaster_total_displacement_rounded": round_and_remove_zero(444444),
            },
        )
        self.assertEqual(
            rows["NPL"],
            {
                "iso3": "NPL",
                "country_name": "Nepal",
                "year": DATA_YEAR,
                "conflict_new_displacement": None,
                "conflict_new_displacement_rounded": None,
                "conflict_total_displacement": 9,
                "conflict_total_displacement_rounded": round_and_remove_zero(9),
                "disaster_new_displacement": None,
                "disaster_new_displacement_rounded": None,
                "disaster_total_displacement": None,
                "disaster_total_displacement_rounded": None,
            },
        )

    def test_all_null_row_is_excluded(self):
        GiddDisplacement.objects.create(
            country=self.country_afg,
            iso3="AFG",
            country_name="Afghanistan",
            year=DATA_YEAR + 1,
            cause=Crisis.CRISIS_TYPE.CONFLICT,
        )
        self.assertEqual(self.get_list(DISPLACEMENTS_URL)["count"], 2)

    def test_list_query_count(self):
        # client lookup + ReleaseMetadata + COUNT + page + StatusLog.last_release_date
        with self.assertNumQueries(5):
            self.client.get(DISPLACEMENTS_URL, {"client_id": self.CLIENT_CODE})


class TestGiddPublicFigureAnalysisRestApi(GiddRestApiMixin, HelixAPITestCase):
    def setUp(self):
        super().setUp()
        PublicFigureAnalysis.objects.create(
            iso3="AFG",
            year=DATA_YEAR,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            figure_category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            figures=54321,
            figures_rounded=54000,
            description="Conflict IDPs analysis.",
            report_raw_id=1,
        )
        # Second enum member for both enum fields + NULL figures/description.
        PublicFigureAnalysis.objects.create(
            iso3="NPL",
            year=DATA_YEAR,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            figure_category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            figures=None,
            figures_rounded=None,
            description=None,
            report_raw_id=2,
        )

    def test_contract_and_values(self):
        payload = self.get_list(PFA_URL)
        self.assert_envelope(payload, 2)
        self.assertEqual(list(payload["results"][0].keys()), PFA_FIELDS)

        rows = self.by_iso3(payload)
        # Enum fields serialize to the integer value; the *_name
        # SerializerMethodFields serialize to the human label.
        self.assertEqual(
            rows["AFG"],
            {
                "iso3": "AFG",
                "year": DATA_YEAR,
                "figure_cause": Crisis.CRISIS_TYPE.CONFLICT.value,
                "figure_cause_name": "Conflict",
                "figure_category": Figure.FIGURE_CATEGORY_TYPES.IDPS.value,
                "figure_category_name": "IDPs",
                "description": "Conflict IDPs analysis.",
                "figures": 54321,
                "figures_rounded": 54000,
            },
        )
        self.assertEqual(
            rows["NPL"],
            {
                "iso3": "NPL",
                "year": DATA_YEAR,
                "figure_cause": Crisis.CRISIS_TYPE.DISASTER.value,
                "figure_cause_name": "Disaster",
                "figure_category": Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value,
                "figure_category_name": "Internal Displacements",
                "description": None,
                "figures": None,
                "figures_rounded": None,
            },
        )

    def test_cause_filter_selects_enum_member(self):
        payload = self.get_list(PFA_URL, cause="disaster")
        self.assertEqual([row["iso3"] for row in payload["results"]], ["NPL"])

    def test_list_query_count(self):
        # client lookup + ReleaseMetadata + COUNT + page + StatusLog.last_release_date
        with self.assertNumQueries(5):
            self.client.get(PFA_URL, {"client_id": self.CLIENT_CODE})


class TestGiddRestApiClientTracking(GiddRestApiMixin, HelixAPITestCase):
    """The client-id tracking hook lives in `get_queryset()` (it calls
    `track_gidd`, which increments a per-day redis counter). A list request must
    therefore evaluate `get_queryset()` exactly once, or every request is counted
    twice against the client's quota."""

    ENDPOINTS = (
        (COUNTRIES_URL, CountryViewSet, ExternalApiDump.ExternalApiType.GIDD_COUNTRY_REST),
        (CONFLICTS_URL, ConflictViewSet, ExternalApiDump.ExternalApiType.GIDD_CONFLICT_REST),
        (DISASTERS_URL, DisasterViewSet, ExternalApiDump.ExternalApiType.GIDD_DISASTER_REST),
        (DISPLACEMENTS_URL, DisplacementDataViewSet, ExternalApiDump.ExternalApiType.GIDD_DISPLACEMENT_REST),
        (PFA_URL, PublicFigureAnalysisViewSet, ExternalApiDump.ExternalApiType.GIDD_PUBLIC_FIGURE_ANALYSIS_REST),
    )

    def test_get_queryset_is_called_once_per_list_request(self):
        for url, viewset, _api_type in self.ENDPOINTS:
            with self.subTest(url=url):
                calls = []
                original = viewset.get_queryset

                def counting_get_queryset(view_self, _original=original, _calls=calls):
                    _calls.append(view_self.request.path)
                    return _original(view_self)

                with patch.object(viewset, "get_queryset", counting_get_queryset):
                    response = self.client.get(url, {"client_id": self.CLIENT_CODE})
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(len(calls), 1, f"{url} evaluated get_queryset {len(calls)} times")

    def test_one_request_increments_the_tracking_counter_once(self):
        for url, _viewset, api_type in self.ENDPOINTS:
            with self.subTest(url=url):
                cache_key = create_client_track_cache_key(api_type, self.CLIENT_CODE)
                external_api_cache.delete(cache_key)
                self.client.get(url, {"client_id": self.CLIENT_CODE})
                self.assertEqual(external_api_cache.get(cache_key), 1)

    def test_unregistered_client_is_rejected(self):
        for url, _viewset, _api_type in self.ENDPOINTS:
            with self.subTest(url=url):
                response = self.client.get(url, {"client_id": "not-a-registered-client"})
                self.assertEqual(response.status_code, 403)
