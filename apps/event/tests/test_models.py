from django.core.exceptions import ValidationError

from apps.crisis.models import Crisis
from apps.event.models import Event, Violence
from utils.factories import CrisisFactory, DisasterCategoryFactory, CountryFactory, EventFactory
from utils.tests import HelixTestCase


class TestEventModel(HelixTestCase):
    def setUp(self) -> None:
        self.data = {
            "crisis": CrisisFactory(),
            "name": "Event1",
            "event_type": Crisis.CRISIS_TYPE.DISASTER,
            "glide_number": "glide number",
            "disaster_category": DisasterCategoryFactory(),
        }

    def test_valid_clean(self):
        event = Event(**self.data)
        self.assertIsNone(event.clean())

    def test_invalid_clean_disaster_without_glide_or_disaster_category(self):
        self.data.pop('glide_number')
        self.data.pop('disaster_category')
        errors = Event.clean_by_event_type(self.data)
        self.assertIn('glide_number', errors)
        self.assertIn('disaster_category', errors)

    def test_invalid_clean_conflict_without_violence(self):
        self.data['event_type'] = Crisis.CRISIS_TYPE.CONFLICT
        errors = Event.clean_by_event_type(self.data)
        self.assertIn('violence', errors)
        violence = Violence(name='abc')
        violence.save()
        self.data['violence'] = violence
        self.assertFalse(Event.clean_by_event_type(self.data))

    def test_invalid_clean_end_smaller_than_start_date(self):
        self.data['end_date'] = '2020-10-12'
        self.data['start_date'] = '2020-10-13'
        errors = Event.clean_dates(self.data)
        self.assertIn('end_date', errors)

    def test_invalid_clean_end_smaller_than_start_date_during_update(self):
        # event with a start date
        event = EventFactory.create(start_date='2020-10-13')
        # try to update with earlier end date
        self.data['end_date'] = '2020-10-12'
        errors = Event.clean_dates(self.data, event)
        self.assertIn('end_date', errors)

        # event without start date
        event = EventFactory.create()
        self.data['end_date'] = '2020-10-12'
        errors = Event.clean_dates(self.data, event)
        self.assertFalse(errors)
