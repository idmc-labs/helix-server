from datetime import date, timedelta

from apps.crisis.models import Crisis
from apps.event.models import Event
from utils.factories import (
    CrisisFactory,
    DisasterSubTypeFactory,
    ViolenceSubTypeFactory,
    EventFactory,
)
from utils.tests import HelixTestCase
from utils.validations import is_child_parent_dates_valid


class TestEventModel(HelixTestCase):
    def setUp(self) -> None:
        self.data = {
            "crisis": CrisisFactory(),
            "name": "Event1",
            "event_type": Crisis.CRISIS_TYPE.DISASTER,
            "glide_number": "glide number",
            "disaster_sub_type": DisasterSubTypeFactory(),
        }

    def test_valid_clean(self):
        event = Event(**self.data)
        self.assertIsNone(event.clean())


class TestGenericValidator(HelixTestCase):
    def test_is_child_parent_dates_valid(self):
        func = is_child_parent_dates_valid

        c_start = _c_start = date.today()
        c_end = _c_end = date.today() + timedelta(days=10)
        p_start = _p_start = c_start - timedelta(days=100)
        p_end = _p_end = c_end + timedelta(days=100)

        errors = func(c_start, c_end, p_start, p_end)
        self.assertFalse(errors)

        c_start = _c_end + timedelta(days=1)
        errors = func(c_start, c_end, p_start, p_end)
        self.assertTrue(errors)
        self.assertIn('start_date', errors)

        c_start = _c_start

        p_start = _c_start + timedelta(days=1)
        errors = func(c_start, c_end, p_start, p_end)
        self.assertTrue(errors)
        self.assertIn('start_date', errors)

        p_start = None
        errors = func(c_start, c_end, p_start, p_end)
        self.assertFalse(errors)

        p_start = _p_start
        c_start = None
        errors = func(c_start, c_end, p_start, p_end)
        self.assertFalse(errors)

        c_start = _c_start

        c_end = _c_start - timedelta(days=1)
        errors = func(c_start, c_end, p_start, p_end)
        self.assertTrue(errors)
        self.assertIn('end_date', errors)

        c_end = _p_end + timedelta(days=1)
        errors = func(c_start, c_end, p_start, p_end)
        self.assertTrue(errors)
        self.assertIn('end_date', errors)

        p_end = None
        c_end = _p_end + timedelta(days=1)
        errors = func(c_start, c_end, p_start, p_end)
        self.assertFalse(errors)

        c_end = None
        p_end = _p_end
        errors = func(c_start, c_end, p_start, p_end)
        self.assertFalse(errors)
