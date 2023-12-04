from utils.tests import HelixTestCase
from utils.factories import (
    CountryFactory,
    CountryRegionFactory,
    CrisisFactory,
    EventFactory,
    EntryFactory,
    TagFactory,
    FigureFactory,
    OrganizationFactory,
    ContextOfViolenceFactory,
)
from apps.extraction.filters import EntryExtractionFilterSet as f, BaseFigureExtractionFilterSet
from apps.crisis.models import Crisis
from apps.entry.models import Figure


class TestExtractionFilter(HelixTestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.reg1 = CountryRegionFactory.create()
        cls.reg2 = CountryRegionFactory.create()
        cls.reg3 = CountryRegionFactory.create()

        cls.fig_cat1 = Figure.FIGURE_CATEGORY_TYPES.IDPS
        cls.fig_cat2 = Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT
        cls.fig_cat3 = Figure.FIGURE_CATEGORY_TYPES.IDPS

        cls.country1reg1 = CountryFactory.create(region=cls.reg1)
        cls.country2reg2 = CountryFactory.create(region=cls.reg2)
        cls.country3reg3 = CountryFactory.create(region=cls.reg3)

        cls.crisis1 = CrisisFactory.create()
        cls.crisis1.countries.set([cls.country1reg1, cls.country2reg2])
        cls.crisis2 = CrisisFactory.create()
        cls.crisis2.countries.set([cls.country3reg3, cls.country2reg2])

        cls.event1crisis1 = EventFactory.create(
            crisis=cls.crisis1,
            event_type=Crisis.CRISIS_TYPE.CONFLICT
        )
        cls.event1crisis1.countries.set([cls.country2reg2])

        cls.event2crisis1 = EventFactory.create(
            crisis=cls.crisis1,
            event_type=Crisis.CRISIS_TYPE.DISASTER
        )
        cls.event2crisis1.countries.set([cls.country1reg1])

        cls.event3crisis2 = EventFactory.create(
            crisis=cls.crisis2,
            event_type=Crisis.CRISIS_TYPE.CONFLICT
        )
        cls.event3crisis2.countries.set([cls.country2reg2, cls.country3reg3])

        cls.tag1 = TagFactory.create()
        cls.tag2 = TagFactory.create()
        cls.tag3 = TagFactory.create()

        cls.org1 = OrganizationFactory.create()
        cls.org2 = OrganizationFactory.create()
        cls.org3 = OrganizationFactory.create()

        cls.entry1event1 = EntryFactory.create(article_title="one")
        cls.figure1entry1event1 = FigureFactory.create(
            entry=cls.entry1event1,
            country=cls.country2reg2,
            category=cls.fig_cat1,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            disaggregation_displacement_rural=100,
            is_housing_destruction=True,
            include_idu=True,
            event=cls.event1crisis1,)

        cls.entry2event2 = EntryFactory.create(article_title="two")
        cls.figure2entry2event2 = FigureFactory.create(
            entry=cls.entry2event2,
            country=cls.country2reg2,
            category=cls.fig_cat2,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            is_housing_destruction=False,
            disaggregation_displacement_urban=100,
            include_idu=True,
            event=cls.event2crisis1,)

        cls.entry3event2 = EntryFactory.create(article_title="three")
        cls.figure3entry3event2 = FigureFactory.create(
            entry=cls.entry3event2,
            category=cls.fig_cat3,
            is_housing_destruction=False,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            country=cls.country3reg3,
            event=cls.event2crisis1,)
        cls.mid_sep = '2020-09-15'
        cls.end_sep = '2020-09-29'
        cls.mid_oct = '2020-10-15'
        cls.end_oct = '2020-10-29'
        cls.mid_nov = '2020-11-16'
        cls.end_nov = '2020-11-29'
        cls.random_event = EventFactory.create(
            crisis=None,
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
        cls.fig1cat1entry1 = FigureFactory.create(
            entry=cls.entry1event1,
            category=cls.fig_cat1,
            start_date=cls.mid_oct,
            end_date=cls.end_oct,
            event=cls.random_event,
            is_housing_destruction=True,
            include_idu=True,
            figure_cause=Crisis.CRISIS_TYPE.OTHER,
        )
        cls.fig2cat2entry1 = FigureFactory.create(
            entry=cls.entry1event1,
            category=cls.fig_cat2,
            start_date=cls.end_oct,
            end_date=cls.end_nov,
            event=cls.random_event,
            is_housing_destruction=True,
            include_idu=True,
            figure_cause=Crisis.CRISIS_TYPE.OTHER,
        )
        cls.fig3cat2entry2 = FigureFactory.create(
            entry=cls.entry2event2, category=cls.fig_cat2,
            start_date=cls.mid_sep, end_date=cls.end_oct, event=cls.random_event,
            figure_cause=Crisis.CRISIS_TYPE.OTHER,
            is_housing_destruction=False,
        )
        cls.fig4cat1entry3 = FigureFactory.create(
            entry=cls.entry3event2,
            category=cls.fig_cat3,
            start_date=cls.mid_nov,
            end_date=None,
            event=cls.random_event,
            figure_cause=Crisis.CRISIS_TYPE.OTHER,
            is_housing_destruction=False,
        )
        cls.fig5cat3entry3 = FigureFactory.create(
            entry=cls.entry3event2, category=cls.fig_cat3,
            start_date=cls.mid_nov, end_date=cls.end_nov, event=cls.random_event,
            figure_cause=Crisis.CRISIS_TYPE.OTHER,
            is_housing_destruction=False,
        )

        cls.fig1cat1entry1.tags.set([cls.tag1])
        cls.fig2cat2entry1.tags.set([cls.tag2])
        cls.fig3cat2entry2.tags.set([cls.tag3])

        cls.context_of_violence = ContextOfViolenceFactory.create()
        cls.figure = FigureFactory.create(
            entry=cls.entry3event2,
            country=cls.country3reg3,
            event=cls.event2crisis1,
            figure_cause=Crisis.CRISIS_TYPE.OTHER,
            is_housing_destruction=False,
        )
        cls.event1crisis1.context_of_violence.set([cls.context_of_violence])
        cls.figure.context_of_violence.set([cls.context_of_violence])

        cls.context_of_violence = ContextOfViolenceFactory.create()
        cls.figure = FigureFactory.create(
            entry=cls.entry3event2,
            country=cls.country3reg3,
            event=cls.event2crisis1,
            figure_cause=Crisis.CRISIS_TYPE.OTHER,
            is_housing_destruction=False,
        )
        cls.event1crisis1.context_of_violence.set([cls.context_of_violence])
        cls.figure.context_of_violence.set([cls.context_of_violence])

    def test_filter_by_region(self):
        regions = [self.reg3.id]
        fqs = f(data=dict(filter_figure_regions=regions)).qs
        self.assertEqual(set(fqs), {self.entry3event2})

    def test_filter_by_figure_crisis_types(self):
        crisis_types = [Crisis.CRISIS_TYPE.CONFLICT, Crisis.CRISIS_TYPE.DISASTER]
        fqs = f(data=dict(filter_figure_crisis_types=crisis_types)).qs
        self.assertEqual(set(fqs), {self.entry3event2, self.entry1event1, self.entry2event2})

        crisis_types = [Crisis.CRISIS_TYPE.CONFLICT]
        fqs = f(data=dict(filter_figure_crisis_types=crisis_types)).qs
        self.assertEqual(set(fqs), {self.entry1event1})

        crisis_types = [Crisis.CRISIS_TYPE.DISASTER]
        fqs = f(data=dict(filter_figure_crisis_types=crisis_types)).qs
        self.assertEqual(set(fqs), {self.entry2event2, self.entry3event2})

    def test_filter_by_country(self):
        data = dict(
            filter_figure_countries=[self.country3reg3.id]
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry3event2})

    def test_filter_by_crises(self):
        data = dict(
            filter_figure_crises=[self.crisis1.id]
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry1event1, self.entry2event2, self.entry3event2})

        data['filter_figure_crises'] = [self.crisis2.id]
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), set())

    def test_filter_by_publishers(self):
        self.entry1event1.publishers.set([self.org1, self.org2])
        self.entry2event2.publishers.set([self.org2])
        self.entry3event2.publishers.set([self.org1, self.org3])
        data = dict(
            filter_entry_publishers=[self.org3.id]
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry3event2})

        data = dict(
            filter_entry_publishers=[self.org2.id]
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry1event1, self.entry2event2})

    def test_filter_by_time_frame(self):
        Figure.objects.all().delete()
        self.fig1cat1entry1 = FigureFactory.create(
            entry=self.entry1event1, category=self.fig_cat1,
            start_date=self.mid_oct, end_date=self.end_oct,
            event=self.random_event,
            figure_cause=Crisis.CRISIS_TYPE.OTHER,
        )
        self.fig2cat2entry1 = FigureFactory.create(
            entry=self.entry1event1, category=self.fig_cat2,
            start_date=self.end_oct, end_date=self.end_nov,
            event=self.random_event,
            figure_cause=Crisis.CRISIS_TYPE.OTHER,
        )
        self.fig3cat2entry2 = FigureFactory.create(
            entry=self.entry2event2, category=self.fig_cat2,
            start_date=self.mid_sep, end_date=self.end_oct,
            event=self.random_event,
            figure_cause=Crisis.CRISIS_TYPE.OTHER,
        )
        self.fig4cat1entry3 = FigureFactory.create(
            entry=self.entry3event2, category=self.fig_cat1,
            start_date=self.mid_nov, end_date=None,
            event=self.random_event,
            figure_cause=Crisis.CRISIS_TYPE.OTHER,
        )
        self.fig5cat3entry3 = FigureFactory.create(
            entry=self.entry3event2, category=self.fig_cat3,
            start_date=self.mid_nov, end_date=self.end_nov,
            event=self.random_event,
            figure_cause=Crisis.CRISIS_TYPE.OTHER,
        )
        data = dict(
            filter_figure_start_after=self.mid_oct,
            figure_end_befor=self.mid_nov,
        )

        data['filter_figure_end_before'] = self.mid_nov
        eqs = {self.entry1event1}
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), eqs)

    def test_filter_by_tags(self):
        data = dict(
            filter_figure_tags=[self.tag1.id]
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry1event1})
        data = dict(
            filter_figure_tags=[self.tag3]
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry2event2})

    def test_filter_by_categories(self):
        data = dict(
            filter_figure_categories=[self.fig_cat1]
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry1event1, self.entry3event2})
        data = dict(
            filter_figure_categories=[self.fig_cat2]
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry1event1, self.entry2event2})

    def test_filter_by_category_types(self):
        data = dict(
            filter_figure_category_types=['FLOW']
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry1event1, self.entry2event2, self.entry3event2})
        data = dict(
            filter_figure_category_types=['STOCK']
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry1event1, self.entry3event2})

    def test_base_entry_filter(self):
        # -- HAS_EXCERPT_IDU
        # True
        data = dict(
            filter_figure_has_excerpt_idu=True,
        )
        fqs = f(data=data).qs
        self.assertEqual(
            set(fqs),
            {self.entry1event1, self.entry2event2},
        )
        # False
        data = dict(
            filter_figure_has_excerpt_idu=False,
        )
        fqs = f(data=data).qs
        assert self.entry1event1 not in set(fqs)
        # -- HAS_HOUSING_DESTRUCTION
        # True
        data = dict(
            filter_figure_has_housing_destruction=True,
        )
        fqs = f(data=data).qs
        self.assertEqual(
            set(fqs),
            {self.entry1event1, },
        )
        # False
        data = dict(
            filter_figure_has_housing_destruction=False,
        )
        fqs = f(data=data).qs
        assert self.entry1event1 not in set(fqs)

    def test_base_figure_filter(self):
        # -- HAS_EXCERPT_IDU
        # True
        data = dict(
            filter_figure_has_excerpt_idu=True,
        )
        fqs = BaseFigureExtractionFilterSet(data=data).qs
        self.assertEqual(
            set(fqs),
            {self.figure1entry1event1, self.figure2entry2event2, self.fig1cat1entry1, self.fig2cat2entry1},
        )
        # False
        data = dict(
            filter_figure_has_excerpt_idu=False,
        )
        fqs = BaseFigureExtractionFilterSet(data=data).qs
        assert all([
            figure not in set(fqs)
            for figure in [self.figure1entry1event1, self.figure2entry2event2, self.fig1cat1entry1, self.fig2cat2entry1]
        ]) is True
        # -- HAS_HOUSING_DESTRUCTION
        # True
        data = dict(
            filter_figure_has_housing_destruction=True,
        )
        fqs = BaseFigureExtractionFilterSet(data=data).qs
        self.assertEqual(
            set(fqs),
            {self.figure1entry1event1, self.fig1cat1entry1, self.fig2cat2entry1},
        )
        # False
        data = dict(
            filter_figure_has_housing_destruction=False,
        )
        fqs = BaseFigureExtractionFilterSet(data=data).qs
        assert all([
            figure not in set(fqs)
            for figure in [self.figure1entry1event1, self.fig1cat1entry1, self.fig2cat2entry1]
        ]) is True
