from django.test import RequestFactory

from apps.event.serializers import EventSerializer
from utils.tests import HelixTestCase
from utils.factories import (
    CrisisFactory,
    CountryFactory,
    EventFactory,
    EntryFactory,
    FigureFactory,
    ViolenceSubTypeFactory,
    DisasterSubCategoryFactory,
    DisasterSubTypeFactory,
)
from apps.crisis.models import Crisis


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

    def test_invalid_event_type(self):
        crisis = CrisisFactory.create(
            crisis_type=Crisis.CRISIS_TYPE.DISASTER.value
        )
        violence_sub_type = ViolenceSubTypeFactory.create()
        data = dict(
            event_type=Crisis.CRISIS_TYPE.CONFLICT.value,
            violence_sub_type=violence_sub_type.pk,
            crisis=crisis.pk,
            name='one',
        )
        serializer = EventSerializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('event_type', serializer.errors)

        data = dict(
            event_type=Crisis.CRISIS_TYPE.DISASTER.value,
            disaster_sub_type=DisasterSubTypeFactory.create().pk,
            crisis=crisis.pk,
            name='one',
        )
        serializer = EventSerializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()


class TestUpdateEventSerializer(HelixTestCase):
    def test_invalid_event_dates_beyond_figure_dates(self):
        from datetime import datetime, timedelta

        start = datetime.today().date()
        end = (datetime.today() + timedelta(days=100)).date()

        crisis = CrisisFactory.create(
            crisis_type=Crisis.CRISIS_TYPE.CONFLICT,
        )
        event = EventFactory.create(
            crisis=crisis,
            event_type=crisis.crisis_type,
            start_date=start,
            end_date=end,
            violence_sub_type=ViolenceSubTypeFactory.create(),
            disaster_sub_type=DisasterSubTypeFactory.create(),
        )
        entry = EntryFactory.create(
            event=event
        )
        figure = FigureFactory.create(
            entry=entry,
            # start and end matches the events
            start_date=event.start_date,
            end_date=event.end_date,
        )
        # no changes, should be valid
        data = dict(
            start_date=event.start_date,
            end_date=event.end_date,
        )
        serializer = EventSerializer(
            instance=event,
            data=data,
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        # now increase the event start, should fail the validation
        data = dict(
            start_date=figure.start_date + timedelta(days=1),
            end_date=figure.end_date,
        )
        serializer = EventSerializer(
            instance=event,
            data=data,
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('start_date', serializer.errors)
        self.assertNotIn('end_date', serializer.errors)

        # now decrease the event end date, should fail the validation
        data = dict(
            start_date=figure.start_date,
            end_date=figure.end_date - timedelta(days=1),
        )
        serializer = EventSerializer(
            instance=event,
            data=data,
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('end_date', serializer.errors)
        self.assertNotIn('start_date', serializer.errors)

    def test_invalid_event_countries_not_including_figure_countries(self):
        c1, c2, c3 = CountryFactory.create_batch(3)

        event = EventFactory.create(
            crisis=None,
            violence_sub_type=ViolenceSubTypeFactory.create(),
            disaster_sub_type=DisasterSubTypeFactory.create(),
        )
        event.countries.set([c1, c2, c3])
        entry = EntryFactory.create(event=event)
        FigureFactory.create(
            entry=entry,
            country=c3
        )

        # validate keeping countries intact, is valid
        data = dict(
            countries=[c1.id, c2.id, c3.id],
        )
        serializer = EventSerializer(
            instance=event,
            data=data,
            partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        # now update event removing the c3, while keeping it in the event
        data = dict(
            countries=[c1.id, c2.id]
        )
        serializer = EventSerializer(
            instance=event,
            data=data,
            partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('countries', serializer.errors)
