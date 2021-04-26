from django.test import RequestFactory

from apps.crisis.serializers import CrisisUpdateSerializer
from utils.tests import HelixTestCase
from utils.factories import (
    CrisisFactory,
    EventFactory,
    CountryFactory,
)


class TestCrisisUpdateSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.context = dict(
            request=RequestFactory().post('/graphql')
        )

    def test_invalid_crisis_date_beyond_children_event_dates(self):
        from datetime import datetime, timedelta

        start = datetime.today()
        end = datetime.today() + timedelta(days=100)

        crisis = CrisisFactory.create(
            start_date=start,
            end_date=end,
        )
        event = EventFactory.create(
            crisis=crisis,
            start_date=start + timedelta(days=1),
        )
        # increase crisis start date more than event start date
        data = dict(
            start_date=event.start_date + timedelta(days=1)
        )
        serializer = CrisisUpdateSerializer(
            instance=crisis,
            data=data,
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('start_date', serializer.errors)

    def test_invalid_crisis_countries_not_including_event_countries(self):
        c1, c2, c3 = CountryFactory.create_batch(3)

        crisis = CrisisFactory.create()
        crisis.countries.set([c1, c2, c3])
        event = EventFactory.create(
            crisis=crisis
        )
        event.countries.set([c1, c2, c3])

        # now update crisis removing the c3, while keeping it in the event
        data = dict(
            countries=[c1.id, c2.id]
        )
        serializer = CrisisUpdateSerializer(
            instance=crisis,
            data=data,
            partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('countries', serializer.errors)
