from apps.crisis.filters import CrisisFilter
from apps.crisis.models import (
    Crisis,
)
from utils.factories import CountryFactory, CrisisFactory, EntryFactory, EventFactory, FigureFactory
from utils.tests import HelixTestCase

CONFLICT = Crisis.CRISIS_TYPE.CONFLICT
DISASTER = Crisis.CRISIS_TYPE.DISASTER


class TestCrisisFilter(HelixTestCase):
    def setUp(self) -> None:
        self.filter_class = CrisisFilter

    def test_name_filter(self):
        CrisisFactory.create(name="one")
        c2 = CrisisFactory.create(name="two")
        c3 = CrisisFactory.create(name="towo")
        # The multi-word search qs has no inherent ORDER BY (the list field applies the
        # production ordering), so order by id here to keep the assertion independent of the
        # DB scan order. TODO: make the search/list ordering deterministic (see FUTURE_WORK).
        obtained = self.filter_class(data=dict(search="wo")).qs.order_by("id")
        expected = [c2, c3]
        self.assertEqual(expected, list(obtained))

    def test_countries_filter(self):
        c1 = CountryFactory.create(name="xyz")
        c2 = CountryFactory.create(name="abc")
        cr1 = CrisisFactory.create()
        cr1.countries.set([c1])
        cr2 = CrisisFactory.create()
        cr2.countries.set([c1, c2])

        obtained = self.filter_class(data=dict(countries=[str(c1.id), str(c2.id)])).qs
        expected = [cr1, cr2]
        self.assertQuerySetEqual(expected, obtained)
        obtained = self.filter_class(data=dict(countries=[str(c2.id)])).qs
        expected = [cr2]
        self.assertQuerySetEqual(expected, obtained)

    def test_crisis_types_filter(self):
        c1 = CrisisFactory.create(crisis_type=CONFLICT)
        c2 = CrisisFactory.create(crisis_type=DISASTER)
        obtained = self.filter_class(data=dict(crisis_types=[CONFLICT.name])).qs
        expected = [c1]
        self.assertQuerySetEqual(expected, obtained)
        obtained = self.filter_class(
            data=dict(
                crisis_types=[
                    CONFLICT.name,
                    DISASTER.name,
                ]
            )
        ).qs
        expected = [c1, c2]
        self.assertQuerySetEqual(expected, obtained)

    def test_crisis_search_by_event_name(self):
        asia_crisis = CrisisFactory.create(crisis_type=DISASTER, name="asia-crisis")
        asia_crisis_1 = CrisisFactory.create(crisis_type=CONFLICT, name="asia-crisis-1")
        asia_crisis_2 = CrisisFactory.create(crisis_type=DISASTER, name="asia-crisis-2")

        asia_crisis_3 = CrisisFactory.create(crisis_type=DISASTER, name="asia-crisis-3")
        CrisisFactory.create(crisis_type=DISASTER, name="africa-crisis")

        EventFactory.create(name="nepal-event-1", crisis=asia_crisis_1)
        EventFactory.create(name="nepal-event-2", crisis=asia_crisis_1)

        EventFactory.create(name="india-event-1", crisis=asia_crisis_2)
        EventFactory.create(name="india-event-2", crisis=asia_crisis_2)

        obtained = self.filter_class(data=dict(search="asia")).qs

        expected = [asia_crisis, asia_crisis_1, asia_crisis_2, asia_crisis_3]
        self.assertQuerySetEqual(expected, obtained)

        obtained = self.filter_class(data=dict(search="nepal")).qs
        expected = [asia_crisis_1]
        self.assertQuerySetEqual(expected, obtained)

        obtained = self.filter_class(data=dict(search="asia", crisis_types=[CONFLICT])).qs
        expected = [asia_crisis_1]
        self.assertQuerySetEqual(expected, obtained)

    def test_event_count_ordering_not_inflated_by_review_count_join(self):
        """`event_count` must count events, not the figures joined in by a review count.

        `annotate_review_figures_count()` aggregates `events__figures`, and Django reuses the
        `events` join for both annotations — so a bare `Count("events")` counts figure rows.
        The list would then be ordered by a number the client never sees, because the
        displayed `eventCount` comes from `EventCountLoader`.
        """
        entry = EntryFactory.create()
        # one event carrying 3 figures ...
        few_events = CrisisFactory.create(name="few-events")
        event = EventFactory.create(crisis=few_events)
        FigureFactory.create_batch(3, entry=entry, event=event)
        # ... versus two events carrying one figure each.
        many_events = CrisisFactory.create(name="many-events")
        for _ in range(2):
            FigureFactory.create(entry=entry, event=EventFactory.create(crisis=many_events))

        qs = self.filter_class(data={}, ordering="event_count,review_not_started_count").qs
        counts = {crisis.id: crisis.event_count for crisis in qs}

        self.assertEqual(counts[few_events.id], 1)
        self.assertEqual(counts[many_events.id], 2)
