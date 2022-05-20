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
)
from apps.extraction.filters import EntryExtractionFilterSet as f
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

        cls.entry1ev1 = EntryFactory.create(article_title="one")
        FigureFactory.create(entry=cls.entry1ev1,
                             country=cls.country2reg2,
                             disaggregation_displacement_rural=100,
                             event=cls.event1crisis1,)
        cls.entry2ev1 = EntryFactory.create(article_title="two")
        FigureFactory.create(entry=cls.entry2ev1,
                             country=cls.country2reg2,
                             disaggregation_displacement_urban=100,
                             event=cls.event1crisis1,)
        cls.entry3ev2 = EntryFactory.create(article_title="three")
        FigureFactory.create(entry=cls.entry3ev2,
                             country=cls.country3reg3,
                             event=cls.event2crisis1,)
        cls.mid_sep = '2020-09-15'
        cls.end_sep = '2020-09-29'
        cls.mid_oct = '2020-10-15'
        cls.end_oct = '2020-10-29'
        cls.mid_nov = '2020-11-16'
        cls.end_nov = '2020-11-29'
        cls.fig1cat1entry1 = FigureFactory.create(
            entry=cls.entry1ev1, category=cls.fig_cat1,
            start_date=cls.mid_oct, end_date=cls.end_oct, event=None
        )
        cls.fig2cat2entry1 = FigureFactory.create(
            entry=cls.entry1ev1, category=cls.fig_cat2,
            start_date=cls.end_oct, end_date=cls.end_nov, event=None
        )
        cls.fig3cat2entry2 = FigureFactory.create(
            entry=cls.entry2ev1, category=cls.fig_cat2,
            start_date=cls.mid_sep, end_date=cls.end_oct, event=None
        )
        cls.fig4cat1entry3 = FigureFactory.create(
            entry=cls.entry3ev2, category=cls.fig_cat3,
            start_date=cls.mid_nov, end_date=None, event=None
        )
        cls.fig5cat3entry3 = FigureFactory.create(
            entry=cls.entry3ev2, category=cls.fig_cat3,
            start_date=cls.mid_nov, end_date=cls.end_nov, event=None
        )

        cls.fig1cat1entry1.tags.set([cls.tag1])
        cls.fig2cat2entry1.tags.set([cls.tag2])
        cls.fig3cat2entry2.tags.set([cls.tag3])

    def test_filter_by_region(self):
        regions = [self.reg3.id]
        fqs = f(data=dict(filter_figure_regions=regions)).qs
        self.assertEqual(set(fqs), {self.entry3ev2})

    def test_filter_by_filter_event_crisis_types(self):
        crisis_types = [Crisis.CRISIS_TYPE.DISASTER]
        fqs = f(data=dict(filter_event_crisis_types=crisis_types)).qs
        self.assertEqual(set(fqs), {self.entry3ev2})

        crisis_types = [Crisis.CRISIS_TYPE.CONFLICT]
        fqs = f(data=dict(filter_event_crisis_types=crisis_types)).qs
        self.assertEqual(set(fqs), {self.entry1ev1, self.entry2ev1})

        # now from client
        crisis_types = ["CONFLICT", "DISASTER"]
        fqs = f(data=dict(filter_event_crisis_types=crisis_types)).qs
        self.assertEqual(set(fqs), {self.entry3ev2, self.entry1ev1, self.entry2ev1})

    def test_filter_by_country(self):
        data = dict(
            filter_figure_countries=[self.country3reg3.id]
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry3ev2})

    def test_filter_by_crises(self):
        data = dict(
            filter_event_crises=[self.crisis1.id]
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry1ev1, self.entry2ev1, self.entry3ev2})

        data['filter_event_crises'] = [self.crisis2.id]
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), set())

    def test_filter_by_publishers(self):
        self.entry1ev1.publishers.set([self.org1, self.org2])
        self.entry2ev1.publishers.set([self.org2])
        self.entry3ev2.publishers.set([self.org1, self.org3])
        data = dict(
            filter_entry_publishers=[self.org3.id]
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry3ev2})

        data = dict(
            filter_entry_publishers=[self.org2.id]
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry1ev1, self.entry2ev1})

    def test_filter_by_displacement_types(self):
        data = dict(
            filter_figure_displacement_types=['RURAL']
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry1ev1})
        self.assertNotIn(self.entry3ev2, fqs)

        data = dict(
            filter_figure_displacement_types=['URBAN']
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry2ev1})
        self.assertNotIn(self.entry3ev2, fqs)

        data = dict(
            filter_figure_displacement_types=['URBAN', 'RURAL']
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry1ev1, self.entry2ev1})
        self.assertNotIn(self.entry3ev2, fqs)

    def test_filter_by_time_frame(self):
        Figure.objects.all().delete()
        self.fig1cat1entry1 = FigureFactory.create(entry=self.entry1ev1, category=self.fig_cat1,
                                                   start_date=self.mid_oct, end_date=self.end_oct)
        self.fig2cat2entry1 = FigureFactory.create(entry=self.entry1ev1, category=self.fig_cat2,
                                                   start_date=self.end_oct, end_date=self.end_nov)
        self.fig3cat2entry2 = FigureFactory.create(entry=self.entry2ev1, category=self.fig_cat2,
                                                   start_date=self.mid_sep, end_date=self.end_oct)
        self.fig4cat1entry3 = FigureFactory.create(entry=self.entry3ev2, category=self.fig_cat1,
                                                   start_date=self.mid_nov, end_date=None)
        self.fig5cat3entry3 = FigureFactory.create(entry=self.entry3ev2, category=self.fig_cat3,
                                                   start_date=self.mid_nov, end_date=self.end_nov)
        data = dict(
            filter_figure_start_after=self.mid_oct,
            figure_end_befor=self.mid_nov,
        )

        data['filter_figure_end_before'] = self.mid_nov
        eqs = {self.entry1ev1}
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), eqs)

    def test_filter_by_tags(self):
        data = dict(
            filter_figure_tags=[self.tag1.id]
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry1ev1})
        data = dict(
            filter_figure_tags=[self.tag3]
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry2ev1})

    def test_filter_by_categories(self):
        data = dict(
            filter_figure_categories=[self.fig_cat1]
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry1ev1, self.entry3ev2})
        data = dict(
            filter_figure_categories=[self.fig_cat2]
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry1ev1, self.entry2ev1})

    def test_filter_by_category_types(self):
        data = dict(
            filter_figure_category_types=['FLOW']
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry1ev1, self.entry2ev1})
        data = dict(
            filter_figure_category_types=['STOCK']
        )
        fqs = f(data=data).qs
        self.assertEqual(set(fqs), {self.entry1ev1, self.entry3ev2})
