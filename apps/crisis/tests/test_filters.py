from apps.crisis.filters import CrisisFilter
from apps.crisis.models import (
    Crisis,
)
from utils.factories import (
    CrisisFactory,
    CountryFactory,
)
from utils.tests import HelixTestCase

CONFLICT = Crisis.CRISIS_TYPE.CONFLICT
DISASTER = Crisis.CRISIS_TYPE.DISASTER


class TestCrisisFilter(HelixTestCase):
    def setUp(self) -> None:
        self.filter_class = CrisisFilter

    def test_name_filter(self):
        CrisisFactory.create(name='one')
        c2 = CrisisFactory.create(name='two')
        c3 = CrisisFactory.create(name='towo')
        obtained = self.filter_class(data=dict(
            name='w'
        )).qs
        expected = [c2, c3]
        self.assertEqual(
            expected,
            list(obtained)
        )

    def test_countries_filter(self):
        c1 = CountryFactory.create(name='xyz')
        c2 = CountryFactory.create(name='abc')
        cr1 = CrisisFactory.create()
        cr1.countries.set([c1])
        cr2 = CrisisFactory.create()
        cr2.countries.set([c1, c2])

        obtained = self.filter_class(data=dict(
            countries=[str(c1.id), str(c2.id)]
        )).qs
        expected = [cr1, cr2]
        self.assertQuerySetEqual(
            expected,
            obtained
        )
        obtained = self.filter_class(data=dict(
            countries=[str(c2.id)]
        )).qs
        expected = [cr2]
        self.assertQuerySetEqual(
            expected,
            obtained
        )

    def test_crisis_types_filter(self):
        c1 = CrisisFactory.create(crisis_type=CONFLICT)
        c2 = CrisisFactory.create(crisis_type=DISASTER)
        obtained = self.filter_class(data=dict(
            crisis_types=[
                CONFLICT.name
            ]
        )).qs
        expected = [c1]
        self.assertQuerySetEqual(
            expected,
            obtained
        )
        obtained = self.filter_class(data=dict(
            crisis_types=[
                CONFLICT.name,
                DISASTER.name,
            ]
        )).qs
        expected = [c1, c2]
        self.assertQuerySetEqual(
            expected,
            obtained
        )
