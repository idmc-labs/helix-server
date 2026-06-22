from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.event.models import Event
from apps.users.enums import USER_ROLE
from utils.factories import (
    CrisisFactory,
    EventFactory,
    FigureFactory,
)
from utils.tests import HelixTestCase, create_user_with_role


class TestExcelExportAggregateFigures(HelixTestCase):
    """Regression guard for ``Event.get_excel_sheets_data`` /
    ``Crisis.get_excel_sheets_data``.

    Both excel exports build the queryset from their list FilterSet (``EventFilter`` /
    ``CrisisFilter``). The list filterset no longer annotates the figure disaggregation
    (``total_stock_idp_figures`` / ``total_flow_nd_figures``) by default -- it is gated and
    resolved by dataloaders for the list view -- *except* when the filter carries an
    ``aggregate_figures`` filter, in which case the qs IS annotated with the
    aggregate-filtered (subset) values.

    The export must add the default (whole-history) annotation only when it is NOT already
    present. The bug this guards: an UNCONDITIONAL re-annotation overwrote the
    aggregate_figures-filtered IDP/ND values with the whole-history default, so a filtered
    export silently shipped wrong totals.

    Data shape (all figures on a single RECOMMENDED-role event under a single crisis, all
    inside calendar year 2022 so ND figures have ``year_difference == 0``):

      IDPS:  A end=2022-03-31 total=100 ; B end=2022-06-30 total=50  (B is the latest)
      ND:    C end=2022-02-10 total=8   ; D end=2022-06-01 total=200

    Whole-history default:
      * IDP reference date = latest IDPS end_date = 2022-06-30 -> IDP = 50 (only B)
      * ND = 8 + 200 = 208
    Filtered with ``filter_figure_end_before = 2022-04-01`` (drops B and D):
      * subset = {A (IDPS), C (ND)}
      * IDP reference date = latest IDPS end_date in subset = 2022-03-31 -> IDP = 100 (A)
      * ND = 8 (only C)

    So the filtered totals (IDP=100, ND=8) differ from the default (IDP=50, ND=208); the
    bug would export the default values for a filtered request.
    """

    # Whole-history (unfiltered) expected aggregate.
    DEFAULT_IDP = 50
    DEFAULT_ND = 208
    # aggregate_figures-filtered (subset) expected aggregate.
    FILTERED_IDP = 100
    FILTERED_ND = 8

    AGGREGATE_FILTER = {
        "aggregate_figures": {
            "filter_figures": {
                # Drops the latest IDPS figure (B) and the later ND figure (D), shifting both
                # the IDP reference date and the ND total.
                "filter_figure_end_before": "2022-04-01",
            },
        },
    }

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user_with_role(USER_ROLE.ADMIN.name)
        cls.crisis = CrisisFactory.create(
            crisis_type=Crisis.CRISIS_TYPE.CONFLICT,
            start_date="2022-01-01",
            end_date="2022-12-31",
        )
        cls.event = EventFactory.create(
            crisis=cls.crisis,
            event_type=Crisis.CRISIS_TYPE.CONFLICT,
            start_date="2022-01-01",
            end_date="2022-12-31",
        )

        # IDPS (stock) figures -- IDP total is the sum of those whose end_date equals the
        # latest IDPS end_date (the reference date) within the considered figure set.
        FigureFactory.create(
            event=cls.event,
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            total_figures=100,
            start_date="2022-01-01",
            end_date="2022-03-31",
        )
        FigureFactory.create(
            event=cls.event,
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            total_figures=50,
            start_date="2022-01-01",
            end_date="2022-06-30",
        )

        # NEW_DISPLACEMENT (flow) figures -- ND total is the sum of all such figures in the
        # considered set.
        FigureFactory.create(
            event=cls.event,
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            total_figures=8,
            start_date="2022-01-10",
            end_date="2022-02-10",
        )
        FigureFactory.create(
            event=cls.event,
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            total_figures=200,
            start_date="2022-05-01",
            end_date="2022-06-01",
        )

    @staticmethod
    def _row_for(sheet_data, model, object_id):
        """Pull the single export row for ``object_id`` and return its IDP/ND values.

        ``get_excel_sheets_data`` returns a values()-queryset under "data"; each row is a
        dict keyed by the header keys, which include the IDP/ND annotation field names.
        """
        rows = [row for row in sheet_data["data"] if row["id"] == object_id]
        assert len(rows) == 1, f"expected exactly one export row for {object_id}, got {rows}"
        row = rows[0]
        return row[model.IDP_FIGURES_ANNOTATE], row[model.ND_FIGURES_ANNOTATE]

    def test_event_export_unfiltered_uses_whole_history_default(self):
        # Control: with no aggregate_figures the export annotates the whole-history default.
        sheet_data = Event.get_excel_sheets_data(self.user.id, filters={})
        idp, nd = self._row_for(sheet_data, Event, self.event.id)
        self.assertEqual(idp, self.DEFAULT_IDP)
        self.assertEqual(nd, self.DEFAULT_ND)

    def test_event_export_with_aggregate_figures_ships_filtered_totals(self):
        # Regression: a filtered export must carry the aggregate_figures-filtered totals,
        # NOT the whole-history default (which an unconditional re-annotation would inject).
        sheet_data = Event.get_excel_sheets_data(self.user.id, filters=self.AGGREGATE_FILTER)
        idp, nd = self._row_for(sheet_data, Event, self.event.id)
        self.assertEqual(idp, self.FILTERED_IDP)
        self.assertEqual(nd, self.FILTERED_ND)
        # Guard against the totals accidentally coinciding with the default.
        self.assertNotEqual((idp, nd), (self.DEFAULT_IDP, self.DEFAULT_ND))

    def test_crisis_export_unfiltered_uses_whole_history_default(self):
        sheet_data = Crisis.get_excel_sheets_data(self.user.id, filters={})
        idp, nd = self._row_for(sheet_data, Crisis, self.crisis.id)
        self.assertEqual(idp, self.DEFAULT_IDP)
        self.assertEqual(nd, self.DEFAULT_ND)

    def test_crisis_export_with_aggregate_figures_ships_filtered_totals(self):
        sheet_data = Crisis.get_excel_sheets_data(self.user.id, filters=self.AGGREGATE_FILTER)
        idp, nd = self._row_for(sheet_data, Crisis, self.crisis.id)
        self.assertEqual(idp, self.FILTERED_IDP)
        self.assertEqual(nd, self.FILTERED_ND)
        self.assertNotEqual((idp, nd), (self.DEFAULT_IDP, self.DEFAULT_ND))
