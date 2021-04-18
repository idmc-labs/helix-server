from datetime import datetime, timedelta

from apps.event.filters import EventFilter
from apps.crisis.models import Crisis
from apps.event.models import (
    Event
)
from utils.factories import (
    CountryFactory,
    EventFactory,
    CrisisFactory,
)
from utils.tests import HelixTestCase


CONFLICT = Crisis.CRISIS_TYPE.CONFLICT
DISASTER = Crisis.CRISIS_TYPE.DISASTER


class TestEventFilter(HelixTestCase):
    def setUp(self) -> None:
        self.filter_class = EventFilter

    def test_event_name_filter(self):
        EventFactory.create(name='one')
        e2 = EventFactory.create(name='two')
        obtained = self.filter_class(data=dict(
            name='w'
        )).qs
        expected = [e2]
        self.assertQuerySetEqual(
            expected,
            obtained
        )

    def test_crisis_filter(self):
        c1 = CrisisFactory.create()
        c2 = CrisisFactory.create()
        e1 = EventFactory.create(crisis=c1)
        EventFactory.create(crisis=c2)
        obtained = self.filter_class(data=dict(
            crisis_by_ids=[str(c1.id)]
        )).qs
        expected = [e1]
        self.assertQuerySetEqual(
            expected,
            obtained
        )

    def test_event_types_filter(self):
        e1 = EventFactory.create(event_type=CONFLICT)
        e2 = EventFactory.create(event_type=DISASTER)
        obtained = self.filter_class(data=dict(
            event_types=[
                CONFLICT.name
            ]
        )).qs
        expected = [e1]
        self.assertQuerySetEqual(
            expected,
            obtained
        )
        obtained = self.filter_class(data=dict(
            event_types=[
                CONFLICT.name,
                DISASTER.name,
            ]
        )).qs
        expected = [e1, e2]
        self.assertQuerySetEqual(
            expected,
            obtained
        )

    def test_start_date_filter(self):
        now = datetime.today()
        e1 = EventFactory.create(start_date=now)
        e2 = EventFactory.create(start_date=now + timedelta(days=1))
        expected = [e2]
        check_against = str(now).split(' ')[0]
        self.assertQuerySetEqual(
            Event.objects.filter(start_date__gt=check_against),
            expected
        )
        obtained = self.filter_class(data=dict(
            start_date__gt=check_against
        )).qs
        self.assertQuerySetEqual(
            expected,
            obtained
        )
        obtained = self.filter_class(data=dict(
            start_date__gte=str(now)
        )).qs
        expected = [e1, e2]
        self.assertQuerySetEqual(
            expected,
            obtained
        )

    def test_countries_filter(self):
        c1 = CountryFactory.create()
        c2 = CountryFactory.create()
        c3 = CountryFactory.create()
        e1 = EventFactory.create()
        e1.countries.set([c1, c2])
        e2 = EventFactory.create()
        e2.countries.set([c3, c2])
        obtained = self.filter_class(data=dict(
            countries=[str(c1.id)]
        )).qs
        expected = [e1]
        self.assertQuerySetEqual(
            expected,
            obtained
        )

        obtained = self.filter_class(data=dict(
            countries=[str(c2.id)]
        )).qs
        expected = [e1, e2]
        self.assertQuerySetEqual(
            expected,
            obtained
        )
