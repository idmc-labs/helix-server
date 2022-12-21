from django.test import RequestFactory

from apps.users.enums import USER_ROLE
from apps.event.serializers import EventSerializer
from utils.tests import HelixTestCase, create_user_with_role
from utils.factories import (
    CrisisFactory,
    CountryFactory,
    EventFactory,
    EntryFactory,
    FigureFactory,
    ViolenceSubTypeFactory,
    DisasterSubCategoryFactory,
    DisasterSubTypeFactory,
    DisasterCategoryFactory,
    DisasterTypeFactory,
    ViolenceFactory,
)
from apps.crisis.models import Crisis
from datetime import datetime, timedelta


class TestCreateEventSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.request = RequestFactory().post('/graphql')
        self.request.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.context = dict(
            request=self.request
        )

    def test_invalid_crisis_date_event_serializer(self):
        start = datetime.today()
        end = datetime.today() + timedelta(days=3)

        violence_sub_type = ViolenceSubTypeFactory.create()
        crisis = CrisisFactory.create(
            start_date=start,
            end_date=end,
        )
        data = {
            "crisis": crisis.id,
            "name": "test event",
            "start_date": (start - timedelta(days=1)).strftime('%Y-%m-%d'),
            "end_date": (end + timedelta(days=1)).strftime('%Y-%m-%d'),
            'event_type': int(crisis.crisis_type),
            'violence': violence_sub_type.violence.id,
            'violence_sub_type': violence_sub_type.id,
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
        start_date = datetime.today() - timedelta(days=20)
        end_date = datetime.today() - timedelta(days=10)
        data = dict(
            event_type=Crisis.CRISIS_TYPE.CONFLICT.value,
            violence=violence_sub_type.violence.pk,
            violence_sub_type=violence_sub_type.pk,
            crisis=crisis.pk,
            name='one',
            start_date=start_date.date(),
            end_date=end_date.date(),
            event_narrative="event narrative"
        )
        serializer = EventSerializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('event_type', serializer.errors)

        data = dict(
            event_type=Crisis.CRISIS_TYPE.DISASTER.value,
            disaster_sub_type=DisasterSubTypeFactory.create().pk,
            crisis=crisis.pk,
            name='one',
            start_date=start_date.date(),
            end_date=end_date.date(),
            event_narrative="event narrative2"
        )
        serializer = EventSerializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

    def test_should_save_parent_categories(self):

        disaster_category = DisasterCategoryFactory.create()
        disaster_sub_category = DisasterSubCategoryFactory.create(category=disaster_category)
        disaster_type = DisasterTypeFactory.create(
            disaster_sub_category=disaster_sub_category
        )
        disaster_sub_type = DisasterSubTypeFactory.create(
            type=disaster_type,
        )
        violence = ViolenceFactory.create()
        violence_sub_type = ViolenceSubTypeFactory.create(violence=violence)

        data = {
            'name': 'test event',
            'event_type': Crisis.CRISIS_TYPE.DISASTER.value,
            'start_date': '2020-01-01',
            'end_date': '2021-01-01',
            'disaster_sub_category': disaster_sub_category.id,
            'disaster_sub_type': disaster_sub_type.id,
            'violence_sub_type': violence_sub_type.id,
        }
        serializer = EventSerializer(data=data, context={'request': self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        event = serializer.save()

        # Test sub fields
        self.assertEqual(event.disaster_sub_category.id, disaster_sub_category.id)
        self.assertEqual(event.disaster_sub_type.id, disaster_sub_type.id)
        self.assertEqual(event.violence_sub_type.id, violence_sub_type.id)

        # Test parent fields
        self.assertEqual(event.disaster_category.id, disaster_category.id)
        self.assertEqual(event.disaster_type.id, disaster_type.id)
        self.assertEqual(event.violence.id, violence.id)


class TestUpdateEventSerializer(HelixTestCase):
    def setUp(self):
        self.request = RequestFactory().post('/graphql')
        self.request.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.context = dict(
            request=self.request
        )

    def test_invalid_event_countries_not_including_figure_countries(self):
        c1, c2, c3 = CountryFactory.create_batch(3)
        start_date = datetime.today() - timedelta(days=170)
        end_date = datetime.today() + timedelta(days=70)
        event = EventFactory.create(
            crisis=None,
            violence_sub_type=ViolenceSubTypeFactory.create(),
            disaster_sub_type=DisasterSubTypeFactory.create(),
            start_date=start_date.date(),
            end_date=end_date.date(),
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
            event_narrative="test event narrative"
        )
        event.countries.set([c1, c2, c3])
        entry = EntryFactory.create()
        FigureFactory.create(
            entry=entry,
            country=c3,
            event=event,
        )

        # validate keeping countries intact, is valid
        data = dict(
            countries=[c1.id, c2.id, c3.id],
        )
        serializer = EventSerializer(
            instance=event,
            data=data,
            context=self.context,
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
            context=self.context,
            partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('countries', serializer.errors)
