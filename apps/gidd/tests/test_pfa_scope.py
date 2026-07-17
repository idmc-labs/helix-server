from datetime import date

from django.test import TestCase

from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.gidd.models import PublicFigureAnalysis, StatusLog
from apps.gidd.tasks import update_gidd_data
from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
    ReportFactory,
)
from utils.tests import create_user_with_role

# A PFA total is defined by (year, country, cause, category) and nothing else, so the fixture
# pins one year and spans it fully -- the shape `check_is_pfa_visible_in_gidd` requires.
GIDD_YEAR = 2018
YEAR_START = date(GIDD_YEAR, 1, 1)
YEAR_END = date(GIDD_YEAR, 12, 31)

# Distinct totals, so a value coming from the wrong figure set is visible rather than coincidental.
FIRST_EVENT_FIGURE = 100
SECOND_EVENT_FIGURE = 200
CROSSED_CAUSE_FIGURE = 300


class PublicFigureAnalysisScopeTestCase(TestCase):
    """`update_public_figure_analysis` aggregates on year/country/cause/category only.

    The PFA totals are read off the GIDD report's own figure set, grouped by country, with
    cause and category pinned by the aggregate itself -- not off each PFA report's stored
    filterset. These tests pin the two consequences: a filter a PFA report may not carry
    cannot narrow the published total, and the cause comes from the event rather than the
    figure.
    """

    def setUp(self) -> None:
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.country = CountryFactory.create(name="Nepal", iso3="NEP")
        self.entry = EntryFactory.create(publish_date=date(GIDD_YEAR + 1, 1, 1))

    def _disaster_event(self):
        return EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.DISASTER,
            start_date=YEAR_START,
            end_date=YEAR_END,
        )

    def _new_displacement_figure(self, event, total_figures, figure_cause):
        # NEW_DISPLACEMENT rather than IDPS: the flow aggregate has no reference-date
        # predicate, so the total does not depend on the report's end date.
        return FigureFactory.create(
            entry=self.entry,
            event=event,
            country=self.country,
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            figure_cause=figure_cause,
            total_figures=total_figures,
            start_date=YEAR_START,
            end_date=YEAR_END,
        )

    def _gidd_report(self):
        # `Report.report_figures` is derived from the stored filterset (see
        # `QueryAbstractModel.extract_report_figures`), NOT from the `figures` M2M, so the GIDD
        # report has to carry the year window for its figure set to be the year's figures.
        return ReportFactory.create(
            is_gidd_report=True,
            gidd_report_year=GIDD_YEAR,
            filter_figure_start_after=YEAR_START,
            filter_figure_end_before=YEAR_END,
        )

    def _pfa_report(self, figure_cause, figure_category):
        return ReportFactory.create(
            is_public=True,
            is_pfa_visible_in_gidd=True,
            public_figure_analysis="Analysis text",
            filter_figure_start_after=YEAR_START,
            filter_figure_end_before=YEAR_END,
            filter_figure_categories=[figure_category.value],
            filter_figure_crisis_types=[figure_cause.value],
        )

    def _run_generation(self):
        status_log = StatusLog.objects.create(
            triggered_by=self.user,
            triggered_at=YEAR_START,
            completed_at=YEAR_START,
            status=StatusLog.Status.PENDING,
        )
        update_gidd_data(status_log.id)
        status_log.refresh_from_db()
        # `_generate_gidd_data` swallows every exception and marks the log FAILED, so a green
        # assertion below would otherwise be meaningless.
        assert status_log.status == StatusLog.Status.SUCCESS
        return status_log

    def test_an_event_filter_on_a_pfa_report_does_not_narrow_the_published_total(self):
        first_event = self._disaster_event()
        second_event = self._disaster_event()
        self._new_displacement_figure(first_event, FIRST_EVENT_FIGURE, Crisis.CRISIS_TYPE.DISASTER)
        self._new_displacement_figure(second_event, SECOND_EVENT_FIGURE, Crisis.CRISIS_TYPE.DISASTER)

        gidd_report = self._gidd_report()
        # Non-vacuity guard: the aggregate must see BOTH figures, or the assertion below
        # could pass on an empty/partial figure set.
        assert gidd_report.report_figures.count() == 2

        pfa_report = self._pfa_report(
            Crisis.CRISIS_TYPE.DISASTER,
            Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
        )
        pfa_report.filter_figure_countries.add(self.country)
        # `apps.report.serializers.pfa_disallowed_filters` rejects a PFA report carrying
        # `filter_figure_events`, so this fixture cannot be built through the serializer -- the
        # M2M is set straight on the model instance. That is the point of the test: a row that
        # predates the validation (or is written out of band) must still publish the full
        # country/year total.
        pfa_report.filter_figure_events.add(first_event)

        self._run_generation()

        analysis = PublicFigureAnalysis.objects.get(report=pfa_report)
        assert analysis.iso3 == self.country.iso3
        assert analysis.year == GIDD_YEAR
        assert analysis.figures == FIRST_EVENT_FIGURE + SECOND_EVENT_FIGURE
        # Explicitly not the event-restricted subtotal.
        assert analysis.figures != FIRST_EVENT_FIGURE

    def test_the_cause_is_read_off_the_event_not_the_figure(self):
        event = self._disaster_event()
        figure = self._new_displacement_figure(
            event,
            CROSSED_CAUSE_FIGURE,
            # Disagrees with `event.event_type`; nothing validates the two against each other
            # on write.
            Crisis.CRISIS_TYPE.CONFLICT,
        )
        assert figure.figure_cause == Crisis.CRISIS_TYPE.CONFLICT
        assert event.event_type == Crisis.CRISIS_TYPE.DISASTER

        gidd_report = self._gidd_report()
        assert gidd_report.report_figures.count() == 1

        disaster_report = self._pfa_report(
            Crisis.CRISIS_TYPE.DISASTER,
            Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
        )
        disaster_report.filter_figure_countries.add(self.country)
        # Control: the same country/year/category under the figure's OWN cause. If the cause
        # were read off the figure the two totals would be swapped.
        conflict_report = self._pfa_report(
            Crisis.CRISIS_TYPE.CONFLICT,
            Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
        )
        conflict_report.filter_figure_countries.add(self.country)

        self._run_generation()

        assert PublicFigureAnalysis.objects.get(report=disaster_report).figures == CROSSED_CAUSE_FIGURE
        # No figure hangs off a conflict event, so the conflict sum has no rows at all.
        assert PublicFigureAnalysis.objects.get(report=conflict_report).figures is None
