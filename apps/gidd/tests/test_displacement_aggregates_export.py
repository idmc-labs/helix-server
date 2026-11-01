from datetime import date
from io import BytesIO
from unittest import mock

from django.db.models import Sum
from django.test import TestCase
from openpyxl import load_workbook

from apps.contrib.models import ExcelDownload
from apps.contrib.tasks import get_excel_sheet_content
from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.gidd.models import GiddDisplacement, GiddRelease, StatusLog
from apps.gidd.tasks import get_gidd_years, update_gidd_data
from apps.gidd.utils import UpdatedDisplacementExport, displacement_aggregates
from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
    ReportFactory,
)
from utils.tests import HelixGraphQLTestCase, create_user_with_role

GIDD_YEAR = 2018
YEAR_START = date(GIDD_YEAR, 1, 1)
YEAR_END = date(GIDD_YEAR, 12, 31)

ND = Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT
IDPS = Figure.FIGURE_CATEGORY_TYPES.IDPS
CONFLICT = Crisis.CRISIS_TYPE.CONFLICT
DISASTER = Crisis.CRISIS_TYPE.DISASTER

EXPORT_MUTATION = """
mutation ExportGiddUpdatedDisplacements($filters: UpdatedDisplacementExportFilterDataInputType!) {
    exportGiddUpdatedDisplacements(filters: $filters) {
        ok
        errors
    }
}
"""

HEADERS = ["ISO3", "Country name", "Year", "Cause", "New displacement", "Total displacement"]


def _totals(rows):
    return {(row["iso3"], row["year"], row["cause"]): (row["new_displacement"], row["total_displacement"]) for row in rows}


def _country_names(rows):
    return {(row["iso3"], row["year"], row["cause"]): row["country_name"] for row in rows}


class DisplacementAggregatesTestCase(TestCase):
    """`displacement_aggregates` reproduces GiddDisplacement collapsed to (iso3, year, cause).

    The two share no code: generation rolls Figure up per event and per taxonomy, the query sums
    Figure directly. Right after a generation they read the same figures, so every group must be
    exactly equal -- NULL included, as the release publishes NULL for a missing category.
    """

    def setUp(self) -> None:
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        # `name` differs from `idmc_short_name`, so a query reading the wrong one cannot match the release.
        self.nepal = CountryFactory.create(iso3="NPL", name="Federal Democratic Republic of Nepal", idmc_short_name="Nepal")
        self.india = CountryFactory.create(iso3="IND", name="Republic of India", idmc_short_name="India")
        self.entry = EntryFactory.create(publish_date=date(GIDD_YEAR + 1, 1, 1))
        # Generation only builds the years of GIDD reports.
        ReportFactory.create(
            is_gidd_report=True,
            gidd_report_year=GIDD_YEAR,
            filter_figure_start_after=YEAR_START,
            filter_figure_end_before=YEAR_END,
        )
        self.release = GiddRelease.objects.create(
            name="GIDD 2018",
            version="1.0",
            release_date=date(GIDD_YEAR + 1, 5, 1),
            notes="Test release.",
            created_by=self.user,
        )
        # The factory gives every event its own violence and hazard sub-types, so the two flood
        # events below land in separate GiddDisplacement rows.
        self.flood = EventFactory.create(event_type=DISASTER, start_date=date(GIDD_YEAR - 1, 1, 1), end_date=YEAR_END)
        self.earthquake = EventFactory.create(event_type=DISASTER, start_date=YEAR_START, end_date=YEAR_END)
        self.conflict = EventFactory.create(event_type=CONFLICT, start_date=YEAR_START, end_date=YEAR_END)

    def _figure(self, event, country, category, total_figures, start_date=YEAR_START, end_date=YEAR_END, **kwargs):
        return FigureFactory.create(
            entry=self.entry,
            event=event,
            country=country,
            category=category,
            figure_cause=event.event_type,
            total_figures=total_figures,
            start_date=start_date,
            end_date=end_date,
            **{"role": Figure.ROLE.RECOMMENDED, **kwargs},
        )

    def _run_generation(self):
        status_log = StatusLog.objects.create(
            triggered_by=self.user,
            status=StatusLog.Status.PENDING,
            release=self.release,
        )
        update_gidd_data(status_log.id)
        status_log.refresh_from_db()
        # `_generate_gidd_data` swallows every exception and marks the log FAILED.
        assert status_log.status == StatusLog.Status.SUCCESS
        self.release.refresh_from_db()
        assert self.release.is_live

    @staticmethod
    def _stored_totals():
        return _totals(
            GiddDisplacement.objects.order_by()
            .values("iso3", "year", "cause")
            .annotate(new_displacement=Sum("new_displacement"), total_displacement=Sum("total_displacement"))
        )

    def test_reproduces_stored_release_figures(self):
        self._figure(self.flood, self.nepal, ND, 3000)
        self._figure(self.flood, self.nepal, IDPS, 2500)
        # A flow spanning two years counts in the year it ends.
        self._figure(self.flood, self.nepal, ND, 200, start_date=date(GIDD_YEAR - 1, 6, 1), end_date=date(GIDD_YEAR, 3, 31))
        self._figure(self.earthquake, self.nepal, ND, 800)
        self._figure(self.earthquake, self.nepal, IDPS, 100)
        # IDPS only: no new displacement, so NULL rather than 0.
        self._figure(self.earthquake, self.india, IDPS, 400)
        # ND only: no IDPs, so NULL rather than 0.
        self._figure(self.conflict, self.nepal, ND, 120)
        # Counted by neither side: not recommended, and a stock not dated Dec 31.
        self._figure(self.flood, self.nepal, ND, 99999, role=Figure.ROLE.TRIANGULATION)
        self._figure(self.flood, self.nepal, IDPS, 77777, start_date=YEAR_START, end_date=date(GIDD_YEAR, 6, 30))
        # Outside the GIDD years: generation never builds it.
        self._figure(
            self.flood, self.nepal, ND, 555, start_date=date(GIDD_YEAR + 1, 1, 1), end_date=date(GIDD_YEAR + 1, 6, 30)
        )

        self._run_generation()

        # Non-vacuity: the two disaster events are separate stored rows that the query must merge.
        assert GiddDisplacement.objects.filter(iso3="NPL", year=GIDD_YEAR, cause=DISASTER).count() == 2, (
            "fixture must split NPL disaster across hazard taxonomies"
        )

        expected = {
            ("NPL", GIDD_YEAR, DISASTER): (3000 + 200 + 800, 2500 + 100),
            ("NPL", GIDD_YEAR, CONFLICT): (120, None),
            ("IND", GIDD_YEAR, DISASTER): (None, 400),
        }
        direct = _totals(displacement_aggregates(get_gidd_years()))
        assert direct == expected
        # The pass condition: exact equality on every group.
        assert direct == self._stored_totals()
        # Each group carries the country name the release published for it.
        assert _country_names(displacement_aggregates(get_gidd_years())) == _country_names(
            GiddDisplacement.objects.order_by().values("iso3", "year", "cause", "country_name").distinct()
        )

    def test_without_years_includes_years_outside_the_release(self):
        self._figure(self.flood, self.nepal, ND, 3000)
        self._figure(
            self.flood, self.nepal, ND, 555, start_date=date(GIDD_YEAR + 1, 1, 1), end_date=date(GIDD_YEAR + 1, 6, 30)
        )
        self._run_generation()

        assert _totals(displacement_aggregates()) == {
            ("NPL", GIDD_YEAR, DISASTER): (3000, None),
            ("NPL", GIDD_YEAR + 1, DISASTER): (555, None),
        }
        assert _totals(displacement_aggregates(get_gidd_years())) == self._stored_totals()

    def test_does_not_change_published_data(self):
        self._figure(self.flood, self.nepal, ND, 500)
        self._run_generation()
        published = list(GiddDisplacement.objects.order_by("id").values())

        # Edited after generation: the preview shows it, the published release does not.
        self._figure(self.flood, self.nepal, ND, 200)
        assert _totals(displacement_aggregates(get_gidd_years())) == {("NPL", GIDD_YEAR, DISASTER): (700, None)}
        assert list(GiddDisplacement.objects.order_by("id").values()) == published


class UpdatedDisplacementExportTestCase(HelixGraphQLTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = create_user_with_role(USER_ROLE.GUEST.name)
        # `name` differs from `idmc_short_name`: the export must carry the short name, as the release does.
        self.nepal = CountryFactory.create(iso3="NPL", name="Federal Democratic Republic of Nepal", idmc_short_name="Nepal")
        self.india = CountryFactory.create(iso3="IND", name="Republic of India", idmc_short_name="India")
        self.entry = EntryFactory.create(publish_date=date(GIDD_YEAR + 1, 1, 1))
        for year in (GIDD_YEAR - 1, GIDD_YEAR):
            ReportFactory.create(is_gidd_report=True, gidd_report_year=year)

        disaster = EventFactory.create(event_type=DISASTER)
        conflict = EventFactory.create(event_type=CONFLICT)
        other = EventFactory.create(event_type=Crisis.CRISIS_TYPE.OTHER)
        self._figure(disaster, self.nepal, ND, 3000, GIDD_YEAR)
        self._figure(disaster, self.nepal, IDPS, 2500, GIDD_YEAR)
        # Flows but no stock: the total is unreported, not zero.
        self._figure(conflict, self.nepal, ND, 120, GIDD_YEAR)
        # Measured as zero: stays a zero, distinct from the unreported total above.
        self._figure(conflict, self.india, ND, 0, GIDD_YEAR)
        self._figure(disaster, self.india, ND, 40, GIDD_YEAR - 1)
        # GIDD does not publish OTHER.
        self._figure(other, self.nepal, ND, 999, GIDD_YEAR)
        # Not a year any release covers.
        self._figure(disaster, self.nepal, ND, 555, GIDD_YEAR + 1)

    def _figure(self, event, country, category, total_figures, year):
        return FigureFactory.create(
            entry=self.entry,
            event=event,
            country=country,
            role=Figure.ROLE.RECOMMENDED,
            category=category,
            figure_cause=event.event_type,
            total_figures=total_figures,
            start_date=date(year, 1, 1),
            end_date=date(year, 12, 31),
        )

    def _export_rows(self, filters):
        sheet_data = UpdatedDisplacementExport.get_excel_sheets_data(self.user.id, filters)
        buffer = BytesIO()
        get_excel_sheet_content(**sheet_data).save(buffer)
        rows = list(load_workbook(buffer).active.iter_rows(values_only=True))
        assert list(rows[0]) == HEADERS
        return [list(row) for row in rows[1:]]

    def test_rows_without_filters(self):
        # An empty cell is an unreported measure; 0 stays 0. Values are unrounded.
        assert self._export_rows({}) == [
            ["IND", "India", GIDD_YEAR - 1, "Disaster", 40, None],
            ["IND", "India", GIDD_YEAR, "Conflict", 0, None],
            ["NPL", "Nepal", GIDD_YEAR, "Conflict", 120, None],
            ["NPL", "Nepal", GIDD_YEAR, "Disaster", 3000, 2500],
        ]

    def test_filters(self):
        assert self._export_rows({"iso3_in": ["NPL"]}) == [
            ["NPL", "Nepal", GIDD_YEAR, "Conflict", 120, None],
            ["NPL", "Nepal", GIDD_YEAR, "Disaster", 3000, 2500],
        ]
        assert self._export_rows({"year_gte": GIDD_YEAR - 1, "year_lte": GIDD_YEAR - 1}) == [
            ["IND", "India", GIDD_YEAR - 1, "Disaster", 40, None],
        ]
        # As the client sends it, and as a saved download replays it.
        for cause_in in (["DISASTER"], [DISASTER.value]):
            assert self._export_rows({"cause_in": cause_in}) == [
                ["IND", "India", GIDD_YEAR - 1, "Disaster", 40, None],
                ["NPL", "Nepal", GIDD_YEAR, "Disaster", 3000, 2500],
            ]

    def test_any_logged_in_user_can_export(self):
        self.force_login(self.user)
        filters = {"iso3In": ["NPL"], "yearGte": GIDD_YEAR, "causeIn": ["CONFLICT"]}
        with mock.patch("apps.contrib.tasks.generate_excel_file.delay") as delay:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.query(EXPORT_MUTATION, variables={"filters": filters})
        self.assertResponseNoErrors(response)
        assert response.json()["data"]["exportGiddUpdatedDisplacements"]["ok"] is True

        download = ExcelDownload.objects.get()
        assert download.download_type == ExcelDownload.DOWNLOAD_TYPES.GIDD_UPDATED_DISPLACEMENT
        assert download.created_by == self.user
        delay.assert_called_once()
        # The stored filters replay into the same rows the worker will write.
        assert self._export_rows(download.filters) == [
            ["NPL", "Nepal", GIDD_YEAR, "Conflict", 120, None],
        ]
