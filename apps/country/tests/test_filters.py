from django.utils import timezone

from apps.country.filters import CountryFilter, HouseholdSizeFilter
from apps.country.models import (
    Country,
)
from utils.factories import (
    CountryFactory,
    CrisisFactory,
    EventFactory,
    GeographicalGroupFactory,
    HouseholdSizeFactory,
)
from utils.tests import HelixTestCase


class TestHouseholdSizeFilter(HelixTestCase):
    def setUp(self) -> None:
        # AHHS year
        self.current_year = timezone.now().year

        # Filterset
        self.filter_class = HouseholdSizeFilter

        # Country
        self.c1 = CountryFactory.create(name="Newal")
        self.c2 = CountryFactory.create(name="Nepal")
        self.c3 = CountryFactory.create(name="Wanel")
        self.c4 = CountryFactory.create(name="Palne")
        self.c5 = CountryFactory.create(name="Neighbour Nepal")

        # Householdsize
        self.h1 = HouseholdSizeFactory.create(country=self.c1, year=self.current_year - 1)
        self.h2 = HouseholdSizeFactory.create(country=self.c2, year=self.current_year - 2)
        self.h3 = HouseholdSizeFactory.create(country=self.c3, size=2.0, year=self.current_year - 3)  # 1.0 by default
        self.h4 = HouseholdSizeFactory.create(
            country=self.c4, data_source_category="CENSUS-Nepal", year=self.current_year + 1
        )
        self.h5 = HouseholdSizeFactory.create(country=self.c5, data_source_category="XYZ", year=self.current_year + 2)
        self.h6 = HouseholdSizeFactory.create(country=self.c4, year=self.current_year)

    def test_householdsize_filter_by_search(self):
        QUERY = "nepal"
        obtained = self.filter_class(data=dict(search=QUERY)).qs
        expected = [self.h2, self.h4, self.h5]

        self.assertEqual(expected, list(obtained))

    def test_householdsize_filter_by_year(self):
        QUERY = self.current_year
        obtained = self.filter_class(data=dict(year=QUERY)).qs
        expected = [self.h6]

        self.assertEqual(expected, list(obtained))


class TestCountryFilter(HelixTestCase):
    def setUp(self) -> None:
        self.filter_class = CountryFilter
        self.c1 = CountryFactory.create(idmc_short_name="Newal")
        self.c2 = CountryFactory.create(idmc_short_name="Nepal")
        self.c3 = CountryFactory.create(idmc_short_name="Wanel")
        self.c4 = CountryFactory.create(idmc_short_name="Palne")

    def test_country_name_filter(self):
        QUERY = "ne"
        obtained = self.filter_class(data=dict(search=QUERY), queryset=Country.objects.all()).qs
        expected = [self.c1, self.c2, self.c3, self.c4]
        self.assertEqual(expected, list(obtained))

    def test_events_filters(self):
        # filter by event
        c1 = CountryFactory.create(idmc_short_name="test_event")
        c2 = CountryFactory.create(idmc_short_name="test_event2")
        event1 = EventFactory.create()
        event1.countries.add(c1)
        event2 = EventFactory.create()
        event2.countries.add(c2)

        QUERY = [event1.id]
        obtained = self.filter_class(data=dict(events=QUERY), queryset=Country.objects.all()).qs
        expected = [c1]
        self.assertEqual(expected, list(obtained))
        QUERY = [event2.id]
        obtained = self.filter_class(data=dict(events=QUERY), queryset=Country.objects.all()).qs
        expected = [c2]
        self.assertEqual(expected, list(obtained))

    def test_crises_filters(self):
        # filter by crisis
        c1 = CountryFactory.create(idmc_short_name="test_crisis")
        c2 = CountryFactory.create(idmc_short_name="test_crisis2")
        crisis1 = CrisisFactory.create()
        crisis1.countries.add(c1)
        crisis2 = CrisisFactory.create()
        crisis2.countries.add(c2)

        QUERY = [crisis1.id]
        obtained = self.filter_class(data=dict(crises=QUERY), queryset=Country.objects.all()).qs
        expected = [c1]
        self.assertEqual(expected, list(obtained))
        QUERY = [crisis2.id]
        obtained = self.filter_class(data=dict(crises=QUERY), queryset=Country.objects.all()).qs
        expected = [c2]
        self.assertEqual(expected, list(obtained))

    def test_geo_group_ids_filter(self):
        geo = GeographicalGroupFactory.create()
        geo2 = GeographicalGroupFactory.create()
        self.c1.geographical_group = geo
        self.c1.save()
        self.c2.geographical_group = geo
        self.c2.save()
        self.c3.geographical_group = geo2
        self.c3.save()
        obtained = self.filter_class(data=dict(geo_group_by_ids=[str(geo.id)]), queryset=Country.objects.all()).qs
        expected = [self.c1, self.c2]
        self.assertEqual(expected, list(obtained))
