"""A typology filter must narrow every sheet of the workbook, not only the first.

`PublicFigureAnalysis` and `IdpsSaddEstimate` carry no violence or hazard column, so django-filter
drops `violence_sub_type__in` from their filtersets without a word: the request comes back with a
first sheet scoped to one country beside companion sheets covering every country-year in the
release. The narrowing those models can express is the (iso3, year) pairs the first sheet kept, and
that is what these tests pin.
"""

import io

import openpyxl
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.gidd.models import (
    GiddDisplacement,
    GiddEvent,
    GiddFigure,
    IdpsSaddEstimate,
    PublicFigureAnalysis,
    ReleaseMetadata,
    StatusLog,
)
from apps.gidd.rest_filters import (
    COMPANION_SHEET_NARROWING_FILTERS,
    DisaggregationFilterSet,
    DisaggregationPublicFigureAnalysisFilterSet,
    IdpsSaddEstimateFilter,
    PublicFigureAnalysisFilterSet,
    RestDisplacementDataFilterSet,
)
from helix.caches import external_api_cache
from utils.factories import ClientFactory, CountryFactory, ViolenceSubTypeFactory
from utils.tests import HelixAPITestCase

DISPLACEMENT_EXPORT_URL = "/external-api/gidd/displacements/displacement-export/"
DISAGGREGATION_EXPORT_URL = "/external-api/gidd/disaggregations/disaggregation-export/"

RELEASE_YEAR = 2023

CONFLICT = Crisis.CRISIS_TYPE.CONFLICT


class GiddExportNarrowingMixin:
    """Two countries, one carrying each violence sub type, and a context row for both."""

    CLIENT_CODE = "gidd-export-narrowing"

    def setUp(self):
        super().setUp()
        self.gidd_client = ClientFactory.create(code=self.CLIENT_CODE, is_active=True)
        external_api_cache.set("client_ids", [self.CLIENT_CODE], None)

        ReleaseMetadata.objects.create(
            release_year=RELEASE_YEAR,
            pre_release_year=RELEASE_YEAR - 1,
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
        self.iac = ViolenceSubTypeFactory.create(name="IAC")
        self.niac = ViolenceSubTypeFactory.create(name="NIAC")

        for country in (self.afg, self.npl):
            PublicFigureAnalysis.objects.create(
                iso3=country.iso3,
                year=RELEASE_YEAR,
                figure_cause=CONFLICT,
                figure_category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
                figures=1000,
                figures_rounded=1000,
                description=f"Context for {country.iso3}",
                report_raw_id=1,
            )

    def tearDown(self):
        external_api_cache.delete("client_ids")
        super().tearDown()

    def export(self, url, **params):
        response = self.client.get(url, {"client_id": self.CLIENT_CODE, **params})
        self.assertEqual(response.status_code, 200, response.content)
        return openpyxl.load_workbook(io.BytesIO(response.content), read_only=True)

    def country_years(self, workbook, sheet, iso3_column, year_column):
        rows = workbook[sheet].iter_rows(min_row=2, values_only=True)
        return {(row[iso3_column], row[year_column]) for row in rows}


@override_settings(GIDD_EXPORT_CACHE_DISABLED=True)
class TestDisplacementExportSheetNarrowing(GiddExportNarrowingMixin, HelixAPITestCase):
    def setUp(self):
        super().setUp()
        for country, violence_sub_type in ((self.afg, self.iac), (self.npl, self.niac)):
            GiddDisplacement.objects.create(
                country=country,
                iso3=country.iso3,
                country_name=country.idmc_short_name,
                year=RELEASE_YEAR,
                cause=CONFLICT,
                violence_sub_type=violence_sub_type,
                violence_sub_type_name=violence_sub_type.name,
                new_displacement=100,
                new_displacement_rounded=100,
                total_displacement=1000,
                total_displacement_rounded=1000,
            )
            IdpsSaddEstimate.objects.create(
                country=country,
                iso3=country.iso3,
                country_name=country.idmc_short_name,
                year=RELEASE_YEAR,
                sex="Female",
                cause=CONFLICT,
                zero_to_four=1,
                five_to_eleven=2,
                twelve_to_seventeen=3,
                eighteen_to_fiftynine=4,
                sixty_plus=5,
            )

    def context_sheet(self, workbook):
        return self.country_years(workbook, "2_Context_Displacement_data", 0, 1)

    def sadd_sheet(self, workbook):
        return self.country_years(workbook, "3_IDPs_SADD_estimates", 0, 2)

    def test_unfiltered_export_covers_every_country_year(self):
        workbook = self.export(DISPLACEMENT_EXPORT_URL)
        both = {("AFG", RELEASE_YEAR), ("NPL", RELEASE_YEAR)}
        self.assertEqual(self.context_sheet(workbook), both)
        self.assertEqual(self.sadd_sheet(workbook), both)

    def test_violence_sub_type_narrows_the_context_and_sadd_sheets(self):
        workbook = self.export(DISPLACEMENT_EXPORT_URL, violence_sub_type__in=self.iac.pk)
        # NPL carries only the unselected sub type, so it leaves sheet 1 -- and must leave the
        # sheets that describe sheet 1's country-years with it.
        self.assertEqual(self.context_sheet(workbook), {("AFG", RELEASE_YEAR)})
        self.assertEqual(self.sadd_sheet(workbook), {("AFG", RELEASE_YEAR)})

    def test_first_sheet_still_drops_the_unselected_sub_type(self):
        # Non-vacuity for the fixture: sheet 1 must actually distinguish the two countries, or the
        # assertions above would hold for a workbook nothing narrowed.
        workbook = self.export(DISPLACEMENT_EXPORT_URL, violence_sub_type__in=self.iac.pk)
        self.assertEqual(self.country_years(workbook, "1_Displacement_data", 0, 2), {("AFG", RELEASE_YEAR)})

    def test_cause_and_typology_narrow_together(self):
        # Sheet 1 here is a GROUP BY whose `cause` predicate lands in HAVING, so this is the shape
        # that breaks if the subquery loses the aggregates it filters on.
        workbook = self.export(DISPLACEMENT_EXPORT_URL, cause="conflict", violence_sub_type__in=self.iac.pk)
        self.assertEqual(self.context_sheet(workbook), {("AFG", RELEASE_YEAR)})
        self.assertEqual(self.sadd_sheet(workbook), {("AFG", RELEASE_YEAR)})

    def test_iso3_alone_leaves_the_companion_sheets_to_their_own_filter(self):
        # `iso3__in` is a parameter both filtersets carry, so it must narrow them directly rather
        # than through the subquery -- and must keep working when nothing else is supplied.
        workbook = self.export(DISPLACEMENT_EXPORT_URL, iso3__in="NPL")
        self.assertEqual(self.context_sheet(workbook), {("NPL", RELEASE_YEAR)})
        self.assertEqual(self.sadd_sheet(workbook), {("NPL", RELEASE_YEAR)})


@override_settings(GIDD_EXPORT_CACHE_DISABLED=True)
class TestDisaggregationExportSheetNarrowing(GiddExportNarrowingMixin, HelixAPITestCase):
    def setUp(self):
        super().setUp()
        for country, violence_sub_type in ((self.afg, self.iac), (self.npl, self.niac)):
            gidd_event = GiddEvent.objects.create(
                name=f"{country.iso3} unrest",
                cause=CONFLICT,
                violence_sub_type=violence_sub_type,
                violence_sub_type_name=violence_sub_type.name,
            )
            GiddFigure.objects.create(
                iso3=country.iso3,
                country=country,
                country_name=country.idmc_short_name,
                year=RELEASE_YEAR,
                cause=CONFLICT,
                category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
                unit=Figure.UNIT.PERSON,
                total_figures=1000,
                reported=1000,
                violence_sub_type=violence_sub_type,
                violence_sub_type_name=violence_sub_type.name,
                gidd_event=gidd_event,
            )

    def context_sheet(self, workbook):
        return self.country_years(workbook, "2_Context_Displacement_data", 0, 1)

    def test_unfiltered_export_covers_every_country_year(self):
        workbook = self.export(DISAGGREGATION_EXPORT_URL)
        self.assertEqual(self.context_sheet(workbook), {("AFG", RELEASE_YEAR), ("NPL", RELEASE_YEAR)})

    def test_violence_sub_type_narrows_the_context_sheet(self):
        workbook = self.export(DISAGGREGATION_EXPORT_URL, violence_sub_type__in=self.iac.pk)
        self.assertEqual(self.context_sheet(workbook), {("AFG", RELEASE_YEAR)})

    def test_first_sheet_still_drops_the_unselected_sub_type(self):
        # Non-vacuity for the fixture, as above.
        workbook = self.export(DISAGGREGATION_EXPORT_URL, violence_sub_type__in=self.iac.pk)
        self.assertEqual(self.country_years(workbook, "1_Disaggregated_Data", 1, 5), {("AFG", RELEASE_YEAR)})


class TestNarrowingTriggerList(TestCase):
    """The trigger list is written out, so something has to catch it going stale.

    Deriving it from the filtersets was rejected as too implicit, which leaves the risk that a
    typology filter is added to a first sheet and nobody adds it here -- the exact shape of the
    defect this narrowing exists to fix, one level up.
    """

    def test_the_narrowing_trigger_list_covers_every_unshared_filter(self):
        pairs = (
            (RestDisplacementDataFilterSet, PublicFigureAnalysisFilterSet),
            (RestDisplacementDataFilterSet, IdpsSaddEstimateFilter),
            (DisaggregationFilterSet, DisaggregationPublicFigureAnalysisFilterSet),
        )
        listed = set(COMPANION_SHEET_NARROWING_FILTERS)
        for source, target in pairs:
            unshared = set(source.base_filters) - set(target.base_filters)
            missing = unshared - listed
            assert not missing, (
                f"{source.__name__} accepts {sorted(missing)}, which "
                f"{target.__name__} cannot express and COMPANION_SHEET_NARROWING_FILTERS does not list. "
                "Add them there or the companion sheets silently stop narrowing."
            )
