from datetime import date

from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.extraction.filters import FigureExtractionFilterSet
from apps.organization.models import OrganizationKind
from utils.factories import (
    CountryFactory,
    EventFactory,
    FigureFactory,
    FigureLocationFactory,
    OrganizationFactory,
    OrganizationKindFactory,
)
from utils.tests import HelixTestCase


def _figure_ids(data):
    return set(FigureExtractionFilterSet(data=data).qs.values_list("id", flat=True))


def _ordered_filterset_qs(ordering):
    """The sort keys are annotated only for the tokens the client actually orders by, so the
    ordering is a constructor kwarg."""
    return FigureExtractionFilterSet(data={}, ordering=ordering).qs


class TestFigureExtractionRowSets(HelixTestCase):
    """Row-set semantics of the figure extraction filterset.

    These assertions pin behaviour that must hold on every deployment (they
    deliberately avoid list ORDER and any semantics known to differ across
    versions), so the file can run against old and new code alike.
    """

    @classmethod
    def setUpTestData(cls):
        cls.country1 = CountryFactory.create()
        cls.country2 = CountryFactory.create()
        cls.conflict_event = EventFactory.create(event_type=Crisis.CRISIS_TYPE.CONFLICT)
        cls.disaster_event = EventFactory.create(event_type=Crisis.CRISIS_TYPE.DISASTER)

        # NOTE: the crisis-type filter matches on the figure's own cause
        # (figure_cause), NOT its event's type. `conflict_on_disaster_event`
        # below is where the two disagree, so a filter reading the event's
        # type instead returns a different row set.
        # Real figures always carry both dates (older listing rules exclude
        # flow figures without an end date, newer ones do not — keep the
        # fixtures inside the invariant both agree on).
        dates = {"start_date": date(2021, 3, 1), "end_date": date(2021, 4, 1)}
        cls.conflict_idps = FigureFactory.create(
            country=cls.country1,
            event=cls.conflict_event,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            role=Figure.ROLE.RECOMMENDED,
            **dates,
        )
        cls.conflict_nd = FigureFactory.create(
            country=cls.country1,
            event=cls.conflict_event,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            role=Figure.ROLE.RECOMMENDED,
            **dates,
        )
        cls.disaster_nd = FigureFactory.create(
            country=cls.country2,
            event=cls.disaster_event,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            role=Figure.ROLE.RECOMMENDED,
            **dates,
        )
        # A figure whose cause contradicts its event's type. Without it every fixture has
        # country, cause and event type moving together, so the row sets below cannot tell
        # `figure_cause` from `event__event_type` — nor either from the country filter.
        cls.conflict_on_disaster_event = FigureFactory.create(
            country=cls.country2,
            event=cls.disaster_event,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            role=Figure.ROLE.RECOMMENDED,
            **dates,
        )
        cls.all_ids = {
            cls.conflict_idps.id,
            cls.conflict_nd.id,
            cls.disaster_nd.id,
            cls.conflict_on_disaster_event.id,
        }

    def test_no_filter_returns_everything(self):
        self.assertEqual(_figure_ids({}), self.all_ids)

    def test_country_filter(self):
        self.assertEqual(
            _figure_ids({"filter_figure_countries": [self.country1.id]}),
            {self.conflict_idps.id, self.conflict_nd.id},
        )
        self.assertEqual(
            _figure_ids({"filter_figure_countries": [self.country2.id]}),
            {self.disaster_nd.id, self.conflict_on_disaster_event.id},
        )

    def test_crisis_type_filter(self):
        # `conflict_on_disaster_event` is the discriminating row: it is CONFLICT by cause and
        # DISASTER by event, so it belongs to the CONFLICT set and not the DISASTER one.
        self.assertEqual(
            _figure_ids({"filter_figure_crisis_types": [Crisis.CRISIS_TYPE.CONFLICT]}),
            {self.conflict_idps.id, self.conflict_nd.id, self.conflict_on_disaster_event.id},
        )
        self.assertEqual(
            _figure_ids({"filter_figure_crisis_types": [Crisis.CRISIS_TYPE.DISASTER]}),
            {self.disaster_nd.id},
        )
        self.assertEqual(
            _figure_ids({"filter_figure_crisis_types": [Crisis.CRISIS_TYPE.CONFLICT, Crisis.CRISIS_TYPE.DISASTER]}),
            self.all_ids,
        )

    def test_category_filter(self):
        self.assertEqual(
            _figure_ids({"filter_figure_categories": [Figure.FIGURE_CATEGORY_TYPES.IDPS]}),
            {self.conflict_idps.id},
        )
        self.assertEqual(
            _figure_ids({"filter_figure_categories": [Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT]}),
            {self.conflict_nd.id, self.disaster_nd.id, self.conflict_on_disaster_event.id},
        )

    def test_the_fixture_decorrelates_cause_from_event_type(self):
        """Guards the row set above: if this figure ever stops disagreeing with its event, the
        crisis-type assertions silently stop distinguishing the two columns."""
        self.assertEqual(self.conflict_on_disaster_event.figure_cause, Crisis.CRISIS_TYPE.CONFLICT)
        self.assertEqual(self.conflict_on_disaster_event.event.event_type, Crisis.CRISIS_TYPE.DISASTER)

    def test_filters_combine_as_and(self):
        self.assertEqual(
            _figure_ids(
                {
                    "filter_figure_countries": [self.country1.id],
                    "filter_figure_categories": [Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT],
                }
            ),
            {self.conflict_nd.id},
        )


class TestFigureExtractionDateWindow(HelixTestCase):
    """The year-window listing rules: flow figures by their start (or end,
    when the figure spans years); stock figures by end date within the
    window. These rules feed both the interactive lists and GIDD."""

    WINDOW = {
        "filter_figure_start_after": "2021-01-01",
        "filter_figure_end_before": "2021-12-31",
    }

    @classmethod
    def setUpTestData(cls):
        event = EventFactory.create()

        def make(category, start, end):
            return FigureFactory.create(
                event=event,
                category=category,
                role=Figure.ROLE.RECOMMENDED,
                start_date=start,
                end_date=end,
            )

        nd = Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT
        idps = Figure.FIGURE_CATEGORY_TYPES.IDPS
        cls.flow_same_year_in = make(nd, date(2021, 3, 1), date(2021, 4, 1))
        cls.flow_same_year_out = make(nd, date(2020, 3, 1), date(2020, 4, 1))
        cls.flow_multi_year_end_in = make(nd, date(2019, 6, 1), date(2021, 6, 30))
        cls.flow_multi_year_end_out = make(nd, date(2019, 6, 1), date(2022, 6, 30))
        cls.stock_end_in = make(idps, date(2020, 1, 1), date(2021, 6, 30))
        cls.stock_end_before = make(idps, date(2019, 1, 1), date(2020, 12, 31))
        cls.stock_end_after = make(idps, date(2020, 1, 1), date(2022, 6, 30))

    def test_window_membership(self):
        ids = _figure_ids(self.WINDOW)
        self.assertIn(self.flow_same_year_in.id, ids)
        self.assertIn(self.flow_multi_year_end_in.id, ids)
        self.assertIn(self.stock_end_in.id, ids)
        self.assertNotIn(self.flow_same_year_out.id, ids)
        self.assertNotIn(self.flow_multi_year_end_out.id, ids)
        self.assertNotIn(self.stock_end_before.id, ids)
        self.assertNotIn(self.stock_end_after.id, ids)


class TestFigureExtractionSortKeys(HelixTestCase):
    """The computed sort keys (geolocations, sources reliability): values and
    the relative order they produce. Exact string equality of the location
    key is deliberately NOT asserted (older versions assemble it with
    repeated names), only containment and the resulting order."""

    @classmethod
    def setUpTestData(cls):
        event = EventFactory.create()
        common = dict(
            event=event,
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            start_date=date(2021, 3, 1),
            end_date=date(2021, 4, 1),
        )
        cls.fig_alpha = FigureFactory.create(
            geo_locations=[FigureLocationFactory.create(display_name="alpha town")], **common
        )
        cls.fig_beta = FigureFactory.create(
            geo_locations=[FigureLocationFactory.create(display_name="beta village")], **common
        )
        cls.fig_gamma = FigureFactory.create(
            geo_locations=[FigureLocationFactory.create(display_name="gamma city")], **common
        )

        low = OrganizationFactory.create(
            organization_kind=OrganizationKindFactory.create(reliability=OrganizationKind.ORGANIZATION_RELIABILITY.LOW)
        )
        high = OrganizationFactory.create(
            organization_kind=OrganizationKindFactory.create(reliability=OrganizationKind.ORGANIZATION_RELIABILITY.HIGH)
        )
        cls.fig_alpha.sources.set([low, high])
        cls.fig_beta.sources.set([high])

    def _rows(self):
        qs = _ordered_filterset_qs("geolocations,sources_reliability")
        # only the fields BOTH old and new code expose (newer code computes
        # the min/max intermediates inside its aggregation, not on the row)
        return {row["id"]: row for row in qs.values("id", "geolocations", "sources_reliability")}

    def test_geolocations_key_contains_location_name(self):
        rows = self._rows()
        self.assertIn("alpha town", rows[self.fig_alpha.id]["geolocations"])
        self.assertIn("beta village", rows[self.fig_beta.id]["geolocations"])
        self.assertIn("gamma city", rows[self.fig_gamma.id]["geolocations"])

    def test_geolocations_ordering_sequence(self):
        qs = _ordered_filterset_qs("geolocations").filter(id__in=[self.fig_alpha.id, self.fig_beta.id, self.fig_gamma.id])
        self.assertEqual(
            list(qs.order_by("geolocations").values_list("id", flat=True)),
            [self.fig_alpha.id, self.fig_beta.id, self.fig_gamma.id],
        )
        self.assertEqual(
            list(qs.order_by("-geolocations").values_list("id", flat=True)),
            [self.fig_gamma.id, self.fig_beta.id, self.fig_alpha.id],
        )

    def test_sources_reliability_values(self):
        # NOTE: no source filter is active here — a figure's reliability key
        # derives from all its sources.
        rows = self._rows()
        # mixed low/high sources -> the LOW_TO_HIGH bucket; a single high
        # source -> HIGH. Compare as strings: the enum integer comes back as
        # text or int depending on how the version computes the key.
        self.assertEqual(
            str(rows[self.fig_alpha.id]["sources_reliability"]),
            str(Figure.SOURCES_RELIABILITY.LOW_TO_HIGH.value),
        )
        self.assertEqual(
            str(rows[self.fig_beta.id]["sources_reliability"]),
            str(Figure.SOURCES_RELIABILITY.HIGH.value),
        )
        # no sources -> no reliability
        self.assertIsNone(rows[self.fig_gamma.id]["sources_reliability"])


class TestFigureExtractionExplicitOrdering(HelixTestCase):
    """Ordering by a unique-valued real column returns the exact expected
    sequence (unique keys, so no tiebreaker semantics are involved)."""

    @classmethod
    def setUpTestData(cls):
        event = EventFactory.create()
        cls.figures = [
            FigureFactory.create(
                event=event,
                role=Figure.ROLE.RECOMMENDED,
                category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                start_date=date(2021, 3, 1),
                end_date=date(2021, 4, 1),
                total_figures=total,
            )
            for total in (30, 10, 20)
        ]

    def test_order_by_total_figures(self):
        qs = FigureExtractionFilterSet(data={}).qs
        self.assertEqual(
            list(qs.order_by("total_figures").values_list("total_figures", flat=True)),
            [10, 20, 30],
        )
        self.assertEqual(
            list(qs.order_by("-total_figures").values_list("total_figures", flat=True)),
            [30, 20, 10],
        )
