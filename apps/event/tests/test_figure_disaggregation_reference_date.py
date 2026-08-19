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
