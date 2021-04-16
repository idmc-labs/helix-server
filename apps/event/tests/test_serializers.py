from django.test import RequestFactory

from apps.event.serializers import EventSerializer
from utils.tests import HelixTestCase
from utils.factories import (
    CrisisFactory,
    ViolenceSubTypeFactory,
    DisasterSubCategoryFactory,
)


class TestCreateEventSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.context = dict(
            request=RequestFactory().post('/graphql')
        )

    def test_invalid_crisis_date_event_serializer(self):
        from datetime import datetime, timedelta

        start = datetime.today()
        end = datetime.today() + timedelta(days=3)

        crisis = CrisisFactory.create(
            start_date=start,
            end_date=end,
        )
        data = {
            "crisis": crisis.id,
            "name": "test event",
            "start_date": (start - timedelta(days=1)).strftime('%Y-%m-%d'),
            "end_date": end.strftime('%Y-%m-%d'),
            'event_type': int(crisis.crisis_type),
            'violence_sub_type': ViolenceSubTypeFactory.create().id,
            'disaster_sub_category': DisasterSubCategoryFactory.create().id,
        }
        serializer = EventSerializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('start_date', serializer.errors)
