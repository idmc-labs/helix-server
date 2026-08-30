"""Two parameters the GIDD REST surface accepted without honouring.

`displacement-export` re-sorts for the sheet layout, so a requested `ordering` was replaced after
`filter_queryset` had applied it: the caller got a 200, the wrong order, and -- because `ordering`
is part of the export cache key -- another multi-MB object in storage per ignored sort. It is now
refused with the 400 the rest of this surface returns for bad filter input. `disaster-export`
genuinely honours the parameter and is the control case here.

`search` was published by `SearchFilter` on every GIDD list while no viewset defined
`search_fields`, so the backend handed the queryset back untouched. A documented parameter that
cannot narrow anything is worse than an absent one, and only the schema can show it is gone.
"""

import io

import openpyxl
from django.test import override_settings
from django.utils import timezone

from apps.crisis.models import Crisis
from apps.gidd.models import (
    GiddDisplacement,
    GiddEventDisplacement,
    ReleaseMetadata,
    StatusLog,
)
from helix.caches import external_api_cache
from utils.factories import ClientFactory, CountryFactory
from utils.tests import HelixAPITestCase

DISPLACEMENT_EXPORT_URL = "/external-api/gidd/displacements/displacement-export/"
DISASTER_EXPORT_URL = "/external-api/gidd/disasters/disaster-export/"
SCHEMA_URL = "/external-api/api-schema/"

RELEASE_YEAR = 2023
EARLIER_YEAR = RELEASE_YEAR - 1


class GiddExportFixtureMixin:
    """What a GIDD export needs before it returns a workbook."""

    CLIENT_CODE = "gidd-export-ordering"

    def setUp(self):
        super().setUp()
        ClientFactory.create(code=self.CLIENT_CODE, is_active=True)
        external_api_cache.set("client_ids", [self.CLIENT_CODE], None)
        ReleaseMetadata.objects.create(
            release_year=RELEASE_YEAR,
            pre_release_year=EARLIER_YEAR,
            modified_by=self.user,
        )
        StatusLog.objects.create(
            triggered_by=self.user,
            triggered_at=timezone.now(),
            completed_at=timezone.now(),
            status=StatusLog.Status.SUCCESS,
        )
        self.afg = CountryFactory.create(iso3="AFG", iso2="AF", idmc_short_name="Afghanistan")
        self.npl = CountryFactory.create(iso3="NPL", iso2="NP", idmc_short_name="Nepal")

    def tearDown(self):
        external_api_cache.delete("client_ids")
        super().tearDown()

    def get(self, url, **params):
        return self.client.get(url, {"client_id": self.CLIENT_CODE, **params})

    def workbook(self, response):
        return openpyxl.load_workbook(io.BytesIO(response.content), read_only=True)

    def rows(self, workbook, sheet, iso3_column, year_column):
        return [(row[iso3_column], row[year_column]) for row in workbook[sheet].iter_rows(min_row=2, values_only=True)]


@override_settings(GIDD_EXPORT_CACHE_DISABLED=True)
class TestDisplacementExportRefusesOrdering(GiddExportFixtureMixin, HelixAPITestCase):
    def setUp(self):
        super().setUp()
        for country, year in ((self.afg, RELEASE_YEAR), (self.npl, EARLIER_YEAR)):
            GiddDisplacement.objects.create(
                country=country,
                iso3=country.iso3,
                country_name=country.idmc_short_name,
                year=year,
                cause=Crisis.CRISIS_TYPE.CONFLICT,
                new_displacement=100,
                new_displacement_rounded=100,
                total_displacement=1000,
                total_displacement_rounded=1000,
            )

    def test_the_export_still_answers_without_an_ordering(self):
        # Non-vacuity: the refusal below has to be the parameter, not a fixture that returns 400
        # whatever it is sent.
        response = self.get(DISPLACEMENT_EXPORT_URL)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            self.rows(self.workbook(response), "1_Displacement_data", 0, 2),
            [("AFG", RELEASE_YEAR), ("NPL", EARLIER_YEAR)],
        )

    def test_an_ordering_is_refused_rather_than_replaced(self):
        for value in ("year", "-year", "iso3"):
            with self.subTest(ordering=value):
                response = self.get(DISPLACEMENT_EXPORT_URL, ordering=value)
                # The defect: `filter_queryset` applied the sort, `order_by("-year", "iso3")`
                # replaced it, and the caller was served a 200 in an order it did not ask for.
                self.assertEqual(response.status_code, 400, response.content)
                # Readable: the error names the parameter, as JSON rather than as the repr of a
                # dict under the action's spreadsheet renderer.
                self.assertEqual(response["Content-Type"], "application/json")
                self.assertIn("ordering", response.json())

    def test_a_valid_sort_key_is_refused_too(self):
        # `year` resolves fine on the list action, so the refusal is about the action, not about
        # the key being unrecognised.
        self.assertEqual(self.get("/external-api/gidd/displacements/", ordering="year").status_code, 200)
        self.assertEqual(self.get(DISPLACEMENT_EXPORT_URL, ordering="year").status_code, 400)


@override_settings(GIDD_EXPORT_CACHE_DISABLED=True)
class TestDisasterExportStillHonoursOrdering(GiddExportFixtureMixin, HelixAPITestCase):
    """The control case: nothing re-sorts after `filter_queryset`, so the parameter must survive."""

    def setUp(self):
        super().setUp()
        # `iso3` ascending and `year` ascending disagree, so a sort by year is distinguishable
        # from the queryset's own default order.
        for country, year in ((self.afg, RELEASE_YEAR), (self.npl, EARLIER_YEAR)):
            GiddEventDisplacement.objects.create(
                country=country,
                iso3=country.iso3,
                country_name=country.idmc_short_name,
                year=year,
                cause=Crisis.CRISIS_TYPE.DISASTER,
                event_name=f"{country.iso3} flood",
                new_displacement=100,
                new_displacement_rounded=100,
                total_displacement=1000,
                total_displacement_rounded=1000,
            )

    def exported_rows(self, **params):
        response = self.get(DISASTER_EXPORT_URL, **params)
        self.assertEqual(response.status_code, 200, response.content)
        return self.rows(self.workbook(response), "1_Disaster_Displacement_data", 0, 2)

    def test_the_default_order_is_by_iso3(self):
        self.assertEqual(self.exported_rows(), [("AFG", RELEASE_YEAR), ("NPL", EARLIER_YEAR)])

    def test_a_requested_order_is_applied(self):
        self.assertEqual(self.exported_rows(ordering="year"), [("NPL", EARLIER_YEAR), ("AFG", RELEASE_YEAR)])

    def test_an_unknown_key_is_still_refused_here(self):
        self.assertEqual(self.get(DISASTER_EXPORT_URL, ordering="not_a_column").status_code, 400)


class TestGiddSchemaDropsSearch(HelixAPITestCase):
    """`search` must be gone from the published document, and `ordering` must not go with it."""

    def setUp(self):
        super().setUp()
        response = self.client.get(SCHEMA_URL, {"format": "json"})
        self.assertEqual(response.status_code, 200, response.content)
        self.schema = response.json()

    def parameters(self, path):
        return {parameter["name"] for parameter in self.schema["paths"][path]["get"]["parameters"]}

    def gidd_paths(self):
        return [path for path in self.schema["paths"] if "/gidd/" in path]

    def test_no_gidd_path_publishes_search(self):
        published = [path for path in self.gidd_paths() if "search" in self.parameters(path)]
        self.assertEqual(published, [], published)

    def test_the_gidd_paths_are_actually_in_the_document(self):
        # Non-vacuity: an empty path set would satisfy the assertion above on its own.
        self.assertIn("/external-api/gidd/countries/", self.gidd_paths())
        self.assertIn("/external-api/gidd/public-figure-analyses/", self.gidd_paths())

    def test_ordering_survives_on_the_lists_that_honour_it(self):
        self.assertIn("ordering", self.parameters("/external-api/gidd/countries/"))
        self.assertIn("ordering", self.parameters("/external-api/gidd/disasters/disaster-export/"))

    def test_ordering_is_absent_from_the_export_that_refuses_it(self):
        self.assertNotIn("ordering", self.parameters("/external-api/gidd/displacements/displacement-export/"))
