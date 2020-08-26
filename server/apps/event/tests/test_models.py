from django.core.exceptions import ValidationError

from apps.crisis.models import Crisis
from apps.event.models import Event, Violence
from utils.factories import CrisisFactory, DisasterCategoryFactory, CountryFactory
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
        event = Event(**self.data)
        try:
            event.clean()
            self.assertFalse(True, 'event.clean should have failed.')
        except ValidationError as e:
            self.assertIn('glide_number', e.message_dict)
            self.assertIn('disaster_category', e.message_dict)

    def test_invalid_clean_conflict_without_violence(self):
        self.data['event_type'] = Crisis.CRISIS_TYPE.CONFLICT
        event = Event(**self.data)
        try:
            event.clean()
            self.assertFalse(True, 'event.clean should have failed.')
        except ValidationError as e:
            self.assertIn('violence', e.message_dict)
        event.violence = Violence(name='abc')
        self.assertIsNone(event.clean())

    def test_invalid_clean_end_smaller_than_start_date(self):
        self.data['end_date'] = '2020-10-12'
        self.data['start_date'] = '2020-10-13'
        event = Event(**self.data)
        try:
            event.clean()
            self.assertFalse(True, 'event.clean should have failed.')
        except ValidationError as e:
            self.assertIn('end_date', e.message_dict)
