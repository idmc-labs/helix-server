from datetime import datetime, timedelta
from uuid import uuid4

from django.test import RequestFactory

from apps.crisis.models import Crisis
from apps.event.models import EventCode
from apps.event.serializers import EventSerializer
from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    CrisisFactory,
    DisasterCategoryFactory,
    DisasterSubCategoryFactory,
    DisasterSubTypeFactory,
    DisasterTypeFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
    ViolenceFactory,
    ViolenceSubTypeFactory,
)
from utils.tests import HelixTestCase, create_user_with_role


class TestCreateEventSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.request = RequestFactory().post("/graphql")
        self.request.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.context = dict(request=self.request)

    def test_invalid_crisis_date_event_serializer(self):
        start = datetime.today()
        end = datetime.today() + timedelta(days=3)

        violence_sub_type = ViolenceSubTypeFactory.create()
        crisis = CrisisFactory.create(
            start_date=start,
            end_date=end,
        )
        countries = [country.id for country in CountryFactory.create_batch(2)]
        data = {
            "crisis": crisis.id,
            "name": "test event",
            "start_date": (start - timedelta(days=1)).strftime("%Y-%m-%d"),
            "end_date": (end + timedelta(days=1)).strftime("%Y-%m-%d"),
            "event_type": int(crisis.crisis_type),
            "violence": violence_sub_type.violence.id,
            "violence_sub_type": violence_sub_type.id,
            "disaster_sub_category": DisasterSubCategoryFactory.create().id,
            "countries": countries,
            "event_narrative": "event narrative",
        }
        serializer = EventSerializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("start_date", serializer.errors)

    def test_invalid_crisis_less_event_date_order(self):
        # crisis-less event with end_date < start_date must be rejected.
        start = datetime.today()
        data = dict(
            event_type=Crisis.CRISIS_TYPE.DISASTER.value,
            disaster_sub_type=DisasterSubTypeFactory.create().pk,
            name="one",
            start_date=start.date(),
            end_date=(start - timedelta(days=1)).date(),
            event_narrative="event narrative",
            countries=[CountryFactory.create().id],
        )
        serializer = EventSerializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("start_date", serializer.errors)
        self.assertIn("end_date", serializer.errors)

    def test_valid_crisis_less_event_equal_dates(self):
        # start_date == end_date is allowed.
        start = datetime.today()
        data = dict(
            event_type=Crisis.CRISIS_TYPE.DISASTER.value,
            disaster_sub_type=DisasterSubTypeFactory.create().pk,
            name="one",
            start_date=start.date(),
            end_date=start.date(),
            event_narrative="event narrative",
            countries=[CountryFactory.create().id],
        )
        serializer = EventSerializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_event_dates_more_than_10_years_in_future_rejected(self):
        start = datetime.today() + timedelta(days=365 * 11)
        end = start + timedelta(days=1)
        data = dict(
            event_type=Crisis.CRISIS_TYPE.DISASTER.value,
            disaster_sub_type=DisasterSubTypeFactory.create().pk,
            name="one",
            start_date=start.date(),
            end_date=end.date(),
            event_narrative="event narrative",
            countries=[CountryFactory.create().id],
        )
        serializer = EventSerializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("start_date", serializer.errors)
        self.assertIn("end_date", serializer.errors)

    def test_event_dates_within_10_years_accepted(self):
        # boundary: ~9 years in the future is allowed.
        start = datetime.today() + timedelta(days=365 * 9)
        end = start + timedelta(days=1)
        data = dict(
            event_type=Crisis.CRISIS_TYPE.DISASTER.value,
            disaster_sub_type=DisasterSubTypeFactory.create().pk,
            name="one",
            start_date=start.date(),
            end_date=end.date(),
            event_narrative="event narrative",
            countries=[CountryFactory.create().id],
        )
        serializer = EventSerializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_event_type(self):
        country_1 = CountryFactory.create()
        crisis = CrisisFactory.create(crisis_type=Crisis.CRISIS_TYPE.DISASTER.value)
        crisis.countries.add(country_1)
        violence_sub_type = ViolenceSubTypeFactory.create()
        start_date = datetime.today() - timedelta(days=20)
        end_date = datetime.today() - timedelta(days=10)
        data = dict(
            event_type=Crisis.CRISIS_TYPE.CONFLICT.value,
            violence=violence_sub_type.violence.pk,
            violence_sub_type=violence_sub_type.pk,
            crisis=crisis.pk,
            name="one",
            start_date=start_date.date(),
            end_date=end_date.date(),
            event_narrative="event narrative",
            countries=[country_1.id],
        )
        serializer = EventSerializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("event_type", serializer.errors)

        data = dict(
            event_type=Crisis.CRISIS_TYPE.DISASTER.value,
            disaster_sub_type=DisasterSubTypeFactory.create().pk,
            crisis=crisis.pk,
            name="one",
            start_date=start_date.date(),
            end_date=end_date.date(),
            event_narrative="event narrative2",
            countries=[country_1.id],
        )
        serializer = EventSerializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

    def test_event_codes(self):
        country_1 = CountryFactory.create()
        crisis = CrisisFactory.create(crisis_type=Crisis.CRISIS_TYPE.CONFLICT.value)
        crisis.countries.add(country_1)
        violence_sub_type = ViolenceSubTypeFactory.create()
        start_date = datetime.today() - timedelta(days=20)
        end_date = datetime.today() - timedelta(days=10)
        data = dict(
            event_type=Crisis.CRISIS_TYPE.CONFLICT.value,
            violence=violence_sub_type.violence.pk,
            violence_sub_type=violence_sub_type.pk,
            crisis=crisis.pk,
            name="one",
            start_date=start_date.date(),
            end_date=end_date.date(),
            event_narrative="event narrative",
            countries=[country_1.id],
            event_codes=[
                {
                    "country": country_1.id,
                    "event_code": f"NEP-{n}",
                    "uuid": uuid4(),
                    "event_code_type": EventCode.EVENT_CODE_TYPE.GLIDE_NUMBER,
                }
                for n in range(51)
            ],
        )
        serializer = EventSerializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("event_codes", serializer.errors)
        data["event_codes"] = [
            {
                "country": country_1.id,
                "event_code": f"NEP-{n}",
                "uuid": uuid4(),
                "event_code_type": EventCode.EVENT_CODE_TYPE.GLIDE_NUMBER,
            }
            for n in range(50)
        ]

        serializer = EventSerializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

    def test_should_save_parent_categories(self):
        disaster_category = DisasterCategoryFactory.create()
        disaster_sub_category = DisasterSubCategoryFactory.create(category=disaster_category)
        disaster_type = DisasterTypeFactory.create(disaster_sub_category=disaster_sub_category)
        disaster_sub_type = DisasterSubTypeFactory.create(
            type=disaster_type,
        )
        violence = ViolenceFactory.create()
        violence_sub_type = ViolenceSubTypeFactory.create(violence=violence)

        data = {
            "name": "test disaster event",
            "event_type": Crisis.CRISIS_TYPE.DISASTER.value,
            "start_date": "2020-01-01",
            "end_date": "2021-01-01",
            "disaster_sub_type": disaster_sub_type.id,
            "violence_sub_type": violence_sub_type.id,
            "countries": [country.id for country in CountryFactory.create_batch(2)],
            "event_narrative": "event narrative",
        }
        serializer = EventSerializer(data=data, context={"request": self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        event = serializer.save()

        # Test sub fields
        self.assertEqual(event.disaster_sub_category_id, disaster_sub_category.id)
        self.assertEqual(event.disaster_sub_type_id, disaster_sub_type.id)
        self.assertEqual(event.violence_sub_type_id, None)

        # Test parent fields
        self.assertEqual(event.disaster_category_id, disaster_category.id)
        self.assertEqual(event.disaster_type_id, disaster_type.id)
        self.assertEqual(event.violence_id, None)

        data = {
            "name": "test conflict event",
            "event_type": Crisis.CRISIS_TYPE.CONFLICT.value,
            "start_date": "2020-01-01",
            "end_date": "2021-01-01",
            "disaster_sub_type": disaster_sub_type.id,
            "violence_sub_type": violence_sub_type.id,
            "countries": [country.id for country in CountryFactory.create_batch(2)],
            "event_narrative": "event narrative",
        }
        serializer = EventSerializer(data=data, context={"request": self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        event = serializer.save()

        # Test sub fields
        self.assertEqual(event.disaster_sub_category_id, None)
        self.assertEqual(event.disaster_sub_type_id, None)

        # Test parent fields
        self.assertEqual(event.disaster_category_id, None)
        self.assertEqual(event.disaster_type_id, None)
        self.assertEqual(event.violence_id, violence.id)
        self.assertEqual(event.violence_sub_type_id, violence_sub_type.id)


class TestUpdateEventSerializer(HelixTestCase):
    def setUp(self):
        self.request = RequestFactory().post("/graphql")
        self.request.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.context = dict(request=self.request)

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
            event_narrative="test event narrative",
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
        serializer = EventSerializer(instance=event, data=data, context=self.context, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        # now update event removing the c3, while keeping it in the event
        data = dict(countries=[c1.id, c2.id])
        serializer = EventSerializer(instance=event, data=data, context=self.context, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("countries", serializer.errors)

    def test_legacy_bad_date_order_row_editable_on_other_fields(self):
        # decision #1: the date-order check fires only when the date
        # fields are in the payload, so a legacy row with end_date < start_date
        # can still be updated on unrelated fields.
        start_date = datetime.today()
        event = EventFactory.create(
            crisis=None,
            violence_sub_type=None,
            disaster_sub_type=DisasterSubTypeFactory.create(),
            start_date=start_date.date(),
            end_date=(start_date - timedelta(days=5)).date(),
            event_type=Crisis.CRISIS_TYPE.DISASTER.value,
            event_narrative="test event narrative",
        )
        event.countries.set([CountryFactory.create()])

        data = dict(name="renamed event")
        serializer = EventSerializer(instance=event, data=data, context=self.context, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_partial_update_single_date_breaks_order_rejected(self):
        # partial-update gap: a partial update that touches only one date
        # must be checked against the stored value of the other date.
        event = EventFactory.create(
            crisis=None,
            violence_sub_type=None,
            disaster_sub_type=DisasterSubTypeFactory.create(),
            start_date=datetime(2024, 1, 1).date(),
            end_date=datetime(2024, 6, 1).date(),
            event_type=Crisis.CRISIS_TYPE.DISASTER.value,
            event_narrative="test event narrative",
        )
        event.countries.set([CountryFactory.create()])

        data = dict(end_date=datetime(2023, 1, 1).date())
        serializer = EventSerializer(instance=event, data=data, context=self.context, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("end_date", serializer.errors)
        self.assertIn(
            "The start date must be earlier than end date.",
            str(serializer.errors["end_date"]),
        )

    def test_partial_update_single_date_keeps_order_accepted(self):
        # partial-update positive case: updating only end_date to a value
        # still after the stored start_date passes.
        event = EventFactory.create(
            crisis=None,
            violence_sub_type=None,
            disaster_sub_type=DisasterSubTypeFactory.create(),
            start_date=datetime(2024, 1, 1).date(),
            end_date=datetime(2024, 6, 1).date(),
            event_type=Crisis.CRISIS_TYPE.DISASTER.value,
            event_narrative="test event narrative",
        )
        event.countries.set([CountryFactory.create()])

        data = dict(end_date=datetime(2024, 12, 1).date())
        serializer = EventSerializer(instance=event, data=data, context=self.context, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_legacy_future_dated_event_editable_on_other_fields(self):
        # decision #1: the future-date check fires only when the date
        # fields are in the payload, so a legacy event with out-of-bounds dates
        # can still be updated on unrelated fields.
        start_date = datetime.today() + timedelta(days=365 * 20)
        event = EventFactory.create(
            crisis=None,
            violence_sub_type=None,
            disaster_sub_type=DisasterSubTypeFactory.create(),
            start_date=start_date.date(),
            end_date=(start_date + timedelta(days=1)).date(),
            event_type=Crisis.CRISIS_TYPE.DISASTER.value,
            event_narrative="test event narrative",
        )
        event.countries.set([CountryFactory.create()])

        data = dict(name="renamed event")
        serializer = EventSerializer(instance=event, data=data, context=self.context, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
