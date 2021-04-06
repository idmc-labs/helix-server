from apps.country.filters import CountryFilter
from apps.country.models import (
    Country,
)
from utils.factories import (
    CountryFactory,
    CountryRegionFactory,
    GeographicalGroupFactory,
)
from utils.tests import HelixTestCase


class TestCountryFilter(HelixTestCase):
    def setUp(self) -> None:
        self.filter_class = CountryFilter
        self.c1 = CountryFactory.create(name='Newal')
        self.c2 = CountryFactory.create(name='Nepal')
        self.c3 = CountryFactory.create(name='Wanel')
        self.c4 = CountryFactory.create(name='Palne')

    def test_country_name_filter(self):
        QUERY = 'ne'
        obtained = self.filter_class(data=dict(
            country_name=QUERY
        ), queryset=Country.objects.all()).qs
        expected = [self.c2, self.c1, self.c3, self.c4]
        self.assertEqual(
            expected,
            list(obtained)
        )

    def test_region_filter(self):
        reg = CountryRegionFactory.create(name='xyz')
        reg2 = CountryRegionFactory.create(name='abc')
        self.c1.region = reg
        self.c1.save()
        self.c2.region = reg
        self.c2.save()
        self.c3.region = reg2
        self.c3.save()
        obtained = self.filter_class(data=dict(
            region_name=reg.name
        ), queryset=Country.objects.all()).qs
        expected = [self.c1, self.c2]
        self.assertEqual(
            sorted([each.id for each in expected]),
            sorted([each.id for each in obtained])
        )
        obtained = self.filter_class(data=dict(
            region_by_ids=[str(reg2.id)]
        ), queryset=Country.objects.all()).qs
        expected = [self.c3]
        self.assertEqual(
            expected,
            list(obtained)
        )

    def test_geo_group_ids_filter(self):
        geo = GeographicalGroupFactory.create()
        geo2 = GeographicalGroupFactory.create()
        self.c1.geographical_group = geo
        self.c1.save()
        self.c2.geographical_group = geo
        self.c2.save()
        self.c3.geographical_group = geo2
        self.c3.save()
        obtained = self.filter_class(data=dict(
            geo_group_by_ids=[str(geo.id)]
        ), queryset=Country.objects.all()).qs
        expected = [self.c1, self.c2]
        self.assertEqual(
            expected,
            list(obtained)
        )
