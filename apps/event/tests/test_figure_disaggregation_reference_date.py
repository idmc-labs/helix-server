import datetime

from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.event.models import Event
from utils.factories import CrisisFactory, EventFactory, FigureFactory
from utils.tests import HelixTestCase


class TestFigureDisaggregationReferenceDate(HelixTestCase):
    """The IDP (stock) reference date is MAX(end_date) over the IDPS/RECOMMENDED figures, with
    NULL end_dates IGNORED -- a NULL must not be treated as the "latest" date and zero the count.

    Both code paths that compute the disaggregation must agree:
      * ``annotate_total_figure_disaggregation_via_cte`` -- the list sort path (two-stage CTE)
      * ``_total_figure_disaggregation_subquery``        -- the aggregate_figures / per-row path

    Data (single RECOMMENDED event under one crisis, all in calendar year 2022):
      IDPS:  end=2022-03-31 total=100 ; end=2022-06-30 total=50 ; end=NULL total=999
      ND:    end=2022-02-10 total=8   ; end=2022-06-01 total=200

    reference date = MAX(end_date) = 2022-06-30 (the NULL is ignored, not "latest")
      -> IDP = 50  (only the figure whose end_date == the reference date)
      -> ND  = 208 (8 + 200)
    """

    EXPECTED_IDP = 50
    EXPECTED_ND = 208

    @classmethod
    def setUpTestData(cls):
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
        common = dict(event=cls.event, role=Figure.ROLE.RECOMMENDED)
        # IDPS: MAX end_date is 2022-06-30 (total 50). The NULL-end figure (total 999) must be
        # ignored -- the pre-fix logic let a NULL win the DESC ordering and zeroed the count.
        FigureFactory.create(
            **common,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            total_figures=100,
            start_date="2022-01-01",
            end_date="2022-03-31",
        )
        FigureFactory.create(
            **common,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            total_figures=50,
            start_date="2022-01-01",
            end_date="2022-06-30",
        )
        FigureFactory.create(
            **common,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            total_figures=999,
            start_date="2022-01-01",
            end_date=None,
        )
        # NEW_DISPLACEMENT (flow): both counted regardless of date in the default scope.
        FigureFactory.create(
            **common,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            total_figures=8,
            start_date="2022-01-10",
            end_date="2022-02-10",
        )
        FigureFactory.create(
            **common,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            total_figures=200,
            start_date="2022-05-01",
            end_date="2022-06-01",
        )

    @staticmethod
    def _cte_values(model, obj_id):
        obj = model.annotate_total_figure_disaggregation_via_cte(model.objects.filter(id=obj_id)).get()
        return getattr(obj, model.IDP_FIGURES_ANNOTATE), getattr(obj, model.ND_FIGURES_ANNOTATE)

    @staticmethod
    def _subquery_values(model, obj_id):
        obj = model.objects.filter(id=obj_id).annotate(**model._total_figure_disaggregation_subquery()).get()
        return getattr(obj, model.IDP_FIGURES_ANNOTATE), getattr(obj, model.ND_FIGURES_ANNOTATE)

    def test_event_reference_date_is_max_ignoring_null(self):
        cte = self._cte_values(Event, self.event.id)
        sub = self._subquery_values(Event, self.event.id)
        self.assertEqual(cte, (self.EXPECTED_IDP, self.EXPECTED_ND))
        self.assertEqual(sub, (self.EXPECTED_IDP, self.EXPECTED_ND))
        self.assertEqual(cte, sub, "CTE (list sort) and subquery (aggregate path) must agree")

    def test_crisis_reference_date_is_max_ignoring_null(self):
        cte = self._cte_values(Crisis, self.crisis.id)
        sub = self._subquery_values(Crisis, self.crisis.id)
        self.assertEqual(cte, (self.EXPECTED_IDP, self.EXPECTED_ND))
        self.assertEqual(sub, (self.EXPECTED_IDP, self.EXPECTED_ND))
        self.assertEqual(cte, sub, "CTE (list sort) and subquery (aggregate path) must agree")


class TestCrisisFigureDisaggregationScopedAggregate(HelixTestCase):
    """`CrisisFilter` serves `aggregate_figures` from the CTE, passing a filtered figure set and --
    for a report scope -- an explicit reference date. So the crisis CTE must match the subquery
    under those arguments too, not only in the default scope every other test here covers.

    Event deliberately has no counterpart: `EventFilter` keeps the subquery for that path (see the
    comment in `EventFilter.qs`), so its CTE is only ever called in the default scope.

    Same data as `TestFigureDisaggregationReferenceDate`.

    Scoped set (every figure except the one ending 2022-06-30):
      IDPS: end=2022-03-31 total=100 ; end=NULL total=999   -> reference date 2022-03-31, IDP = 100
      ND:   end=2022-02-10 total=8   ; end=2022-06-01 total=200                        -> ND = 208

    Explicit reference date 2022-03-31 over the full set: IDP = 100 (exact end_date match), ND = 208.
    """

    EXPECTED_ND = 208
    SCOPED_REFERENCE_DATE = datetime.date(2022, 3, 31)
    EXPECTED_SCOPED_IDP = 100

    @classmethod
    def setUpTestData(cls):
        cls.crisis = CrisisFactory.create(
            crisis_type=Crisis.CRISIS_TYPE.CONFLICT, start_date="2022-01-01", end_date="2022-12-31"
        )
        cls.event = EventFactory.create(
            crisis=cls.crisis, event_type=Crisis.CRISIS_TYPE.CONFLICT, start_date="2022-01-01", end_date="2022-12-31"
        )
        common = dict(event=cls.event, role=Figure.ROLE.RECOMMENDED)
        for total, end_date in ((100, "2022-03-31"), (50, "2022-06-30"), (999, None)):
            FigureFactory.create(
                **common,
                category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
                total_figures=total,
                start_date="2022-01-01",
                end_date=end_date,
            )
        for total, start_date, end_date in ((8, "2022-01-10", "2022-02-10"), (200, "2022-05-01", "2022-06-01")):
            FigureFactory.create(
                **common,
                category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                total_figures=total,
                start_date=start_date,
                end_date=end_date,
            )

    def _both_paths(self, **scope):
        qs = Crisis.objects.filter(id=self.crisis.id)
        cte = Crisis.annotate_total_figure_disaggregation_via_cte(qs, **scope).get()
        sub = qs.annotate(**Crisis._total_figure_disaggregation_subquery(**scope)).get()
        keys = (
            Crisis.IDP_FIGURES_ANNOTATE,
            Crisis.ND_FIGURES_ANNOTATE,
            Crisis.IDP_FIGURES_REFERENCE_DATE_ANNOTATE,
        )
        return tuple(getattr(cte, key) for key in keys), tuple(getattr(sub, key) for key in keys)

    def test_filtered_scope(self):
        # A scope that removes the figure holding the unscoped reference date, so a helper ignoring
        # `figures` would report the unscoped 50 rather than the scoped 100.
        cte, sub = self._both_paths(figures=Figure.objects.exclude(end_date=datetime.date(2022, 6, 30)))
        self.assertEqual(cte, (self.EXPECTED_SCOPED_IDP, self.EXPECTED_ND, self.SCOPED_REFERENCE_DATE))
        self.assertEqual(cte, sub, "CTE and subquery must agree on a filtered figure scope")

    def test_explicit_reference_date(self):
        cte, sub = self._both_paths(figures=Figure.objects.all(), reference_date=self.SCOPED_REFERENCE_DATE)
        self.assertEqual(cte, (self.EXPECTED_SCOPED_IDP, self.EXPECTED_ND, self.SCOPED_REFERENCE_DATE))
        self.assertEqual(cte, sub, "CTE and subquery must agree on an explicit reference date")


class TestFigureDisaggregationNdOnly(HelixTestCase):
    """An event/crisis with NEW_DISPLACEMENT (flow) figures but NO IDPS (stock) figure must still
    report its real ND total (and IDP 0/None). Regression guard for the CTE structure: CTE2 was
    chained off an IDPS/RECOMMENDED reference-date CTE, so an entity with no IDPS figure never
    appeared -> its total_flow_nd_figures came back NULL on the sort path, while the subquery
    (independent ND correlated subquery) returned the real value.

    Data (RECOMMENDED, one crisis, no IDPS anywhere):
      ND: total=50 (2022) ; total=100 (2022)  -> ND = 150 ; IDP = 0/None
    """

    EXPECTED_ND = 150

    @classmethod
    def setUpTestData(cls):
        cls.crisis = CrisisFactory.create(
            crisis_type=Crisis.CRISIS_TYPE.CONFLICT, start_date="2022-01-01", end_date="2022-12-31"
        )
        cls.event = EventFactory.create(
            crisis=cls.crisis, event_type=Crisis.CRISIS_TYPE.CONFLICT, start_date="2022-01-01", end_date="2022-12-31"
        )
        common = dict(
            event=cls.event,
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
        )
        FigureFactory.create(**common, total_figures=50, start_date="2022-01-10", end_date="2022-02-10")
        FigureFactory.create(**common, total_figures=100, start_date="2022-05-01", end_date="2022-06-01")
        # NO IDPS/stock figure at all.

    def _check(self, model, obj_id):
        cte = model.annotate_total_figure_disaggregation_via_cte(model.objects.filter(id=obj_id)).get()
        sub = model.objects.filter(id=obj_id).annotate(**model._total_figure_disaggregation_subquery()).get()
        cte_idp, cte_nd = getattr(cte, model.IDP_FIGURES_ANNOTATE), getattr(cte, model.ND_FIGURES_ANNOTATE)
        sub_idp, sub_nd = getattr(sub, model.IDP_FIGURES_ANNOTATE), getattr(sub, model.ND_FIGURES_ANNOTATE)
        # The ND-only entity must report its real ND (not NULL/0) and no IDP.
        self.assertEqual(cte_nd, self.EXPECTED_ND, f"{model.__name__} CTE dropped ND for an ND-only entity")
        self.assertEqual(sub_nd, self.EXPECTED_ND)
        self.assertIn(cte_idp, (None, 0))
        self.assertIn(sub_idp, (None, 0))
        self.assertEqual((cte_idp or 0, cte_nd), (sub_idp or 0, sub_nd), "CTE and subquery must agree")

    def test_event_nd_only(self):
        self._check(Event, self.event.id)

    def test_crisis_nd_only(self):
        self._check(Crisis, self.crisis.id)
