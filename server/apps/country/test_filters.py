from apps.country.filters import CountryFilter
from apps.country.models import Country
from utils.factories import CountryFactory
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
