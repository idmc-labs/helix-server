from datetime import datetime, timedelta

from apps.event.filters import EventFilter
from apps.crisis.models import Crisis
from apps.event.models import (
    Event
)
from apps.entry.models import Figure
from utils.factories import (
    CountryFactory,
    EventFactory,
    CrisisFactory,
    ContextOfViolenceFactory,
    EntryFactory,
    FigureFactory,
    OSMNameFactory,
)
from utils.tests import HelixTestCase
from apps.common.enums import QA_RULE_TYPE


CONFLICT = Crisis.CRISIS_TYPE.CONFLICT
DISASTER = Crisis.CRISIS_TYPE.DISASTER


class TestEventFilter(HelixTestCase):
    def setUp(self) -> None:
        self.filter_class = EventFilter

    def test_event_name_filter(self):
        EventFactory.create(
            name='one',
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
        e2 = EventFactory.create(
            name='two',
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
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
        e1 = EventFactory.create(
            crisis=c1,
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
        EventFactory.create(
            crisis=c2,
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
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
        e1 = EventFactory.create(
            start_date=now,
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
        e2 = EventFactory.create(
            start_date=now + timedelta(days=1),
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
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
        e1 = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
        e1.countries.set([c1, c2])
        e2 = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
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

    def test_filter_by_context_of_violences(self):
        event = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
        context_of_violence = ContextOfViolenceFactory.create()
        event.context_of_violence.set([context_of_violence])
        obtained = self.filter_class(data=dict(context_of_violences=[context_of_violence])).qs
        self.assertQuerySetEqual(
            [event],
            obtained
        )

    def test_qs_rules(self):
        # Create a entry without any recommended figures
        event_0 = EventFactory.create()

        event_1 = EventFactory.create(name='event 1', ignore_qa=False)
        event_2 = EventFactory.create(name='event 2', ignore_qa=False)
        event_3 = EventFactory.create(name='event 3', ignore_qa=False)

        entry_1 = EntryFactory.create()
        entry_2 = EntryFactory.create()
        entry_3 = EntryFactory.create()

        geo_location_1 = OSMNameFactory.create(
            name='one'
        )
        geo_location_2 = OSMNameFactory.create(
            name='tow'
        )
        geo_location_3 = OSMNameFactory.create(
            name='three'
        )

        # Create 3 figures without duplicated geo locations
        FigureFactory.create(
            entry=entry_1,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            role=Figure.ROLE.RECOMMENDED,
            event=event_1,
            geo_locations=[geo_location_1, geo_location_2, geo_location_3],
        )

        # Create 3 figures with 2 duplicated geo locations
        FigureFactory.create_batch(
            3,
            entry=entry_2,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            role=Figure.ROLE.RECOMMENDED,
            event=event_2,
            geo_locations=[geo_location_1, geo_location_1, geo_location_2],
        )

        # Create 3 figures with 3 duplicated geo locations
        FigureFactory.create_batch(
            3,
            entry=entry_3,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            role=Figure.ROLE.RECOMMENDED,
            event=event_3,
            geo_locations=[geo_location_1, geo_location_1, geo_location_1],
        )

        # Test event with multiple recommended figures in same locaiton
        filtered_data = self.filter_class(data=dict(
            qa_rule=QA_RULE_TYPE.HAS_MULTIPLE_RECOMMENDED_FIGURES.name
        )).qs
        self.assertEqual(set(filtered_data), {event_2, event_3})

        # Test events with no recommended figures
        filtered_data = self.filter_class(data=dict(
            qa_rule=QA_RULE_TYPE.HAS_NO_RECOMMENDED_FIGURES.name
        )).qs
        self.assertEqual(set(filtered_data), {event_0, })
