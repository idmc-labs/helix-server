from datetime import datetime, timedelta

from django.db.models import Count

from apps.common.enums import QA_RULE_TYPE
from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.event.filters import EventFilter
from apps.event.models import Event
from utils.factories import (
    ContextOfViolenceFactory,
    CountryFactory,
    CrisisFactory,
    EntryFactory,
    EventCodeFactory,
    EventFactory,
    FigureFactory,
    FigureLocationFactory,
    OtherSubtypeFactory,
)
from utils.graphene.pagination import nulls_last_order_queryset
from utils.tests import HelixTestCase

CONFLICT = Crisis.CRISIS_TYPE.CONFLICT
DISASTER = Crisis.CRISIS_TYPE.DISASTER
OTHER = Crisis.CRISIS_TYPE.OTHER


class TestEventFilter(HelixTestCase):
    def setUp(self) -> None:
        self.filter_class = EventFilter

    def test_event_name_filter(self):
        EventFactory.create(
            name="one",
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
        e2 = EventFactory.create(
            name="two",
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
        obtained = self.filter_class(data=dict(search="wo")).qs
        expected = [e2]

        self.assertQuerySetEqual(expected, obtained)

    def test_other_sub_types_filter(self):
        # Same pass-through shape as the violence/disaster sub-type filters: an event of another
        # type is not narrowed by a sub-type that cannot apply to it. `OtherSubTypeObjectType`
        # no longer exposes its events, so pairing this with `event_types` is how one
        # sub-type's events are read.
        sub_type = OtherSubtypeFactory.create()
        other_sub_type = OtherSubtypeFactory.create()
        matching = EventFactory.create(event_type=OTHER, other_sub_type=sub_type)
        EventFactory.create(event_type=OTHER, other_sub_type=other_sub_type)
        conflict = EventFactory.create(event_type=CONFLICT)

        obtained = self.filter_class(data=dict(other_sub_types=[str(sub_type.id)])).qs
        self.assertQuerySetEqual([matching, conflict], obtained)

        obtained = self.filter_class(data=dict(event_types=[OTHER.name], other_sub_types=[str(sub_type.id)])).qs
        self.assertQuerySetEqual([matching], obtained)

        # No value must not narrow anything.
        self.assertEqual(self.filter_class(data=dict(other_sub_types=[])).qs.count(), 3)

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
        obtained = self.filter_class(data=dict(crisis_by_ids=[str(c1.id)])).qs
        expected = [e1]
        self.assertQuerySetEqual(expected, obtained)

    def test_event_types_filter(self):
        e1 = EventFactory.create(event_type=CONFLICT)
        e2 = EventFactory.create(event_type=DISASTER)
        obtained = self.filter_class(data=dict(event_types=[CONFLICT.name])).qs
        expected = [e1]
        self.assertQuerySetEqual(expected, obtained)
        obtained = self.filter_class(
            data=dict(
                event_types=[
                    CONFLICT.name,
                    DISASTER.name,
                ]
            )
        ).qs
        expected = [e1, e2]
        self.assertQuerySetEqual(expected, obtained)

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
        check_against = str(now).split(" ")[0]
        self.assertQuerySetEqual(Event.objects.filter(start_date__gt=check_against), expected)
        obtained = self.filter_class(data=dict(start_date__gt=check_against)).qs
        self.assertQuerySetEqual(expected, obtained)
        obtained = self.filter_class(data=dict(start_date__gte=str(now))).qs
        expected = [e1, e2]
        self.assertQuerySetEqual(expected, obtained)

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
        obtained = self.filter_class(data=dict(countries=[str(c1.id)])).qs
        expected = [e1]
        self.assertQuerySetEqual(expected, obtained)

        obtained = self.filter_class(data=dict(countries=[str(c2.id)])).qs
        expected = [e1, e2]
        self.assertQuerySetEqual(expected, obtained)

    def test_filter_by_context_of_violences(self):
        event = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )
        context_of_violence = ContextOfViolenceFactory.create()
        event.context_of_violence.set([context_of_violence])
        obtained = self.filter_class(data=dict(context_of_violences=[context_of_violence])).qs
        self.assertQuerySetEqual([event], obtained)

    def test_qs_rules(self):
        # Create a entry without any recommended figures
        event_0 = EventFactory.create()

        event_1 = EventFactory.create(name="event 1", ignore_qa=False)
        event_2 = EventFactory.create(name="event 2", ignore_qa=False)
        event_3 = EventFactory.create(name="event 3", ignore_qa=False)

        entry_1 = EntryFactory.create()
        entry_2 = EntryFactory.create()
        entry_3 = EntryFactory.create()

        geo_location_1 = FigureLocationFactory.create(name="one")
        geo_location_2 = FigureLocationFactory.create(name="tow")
        geo_location_3 = FigureLocationFactory.create(name="three")

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

        # Test event with multiple recommended figures in same location
        filtered_data = self.filter_class(data=dict(qa_rule=QA_RULE_TYPE.HAS_MULTIPLE_RECOMMENDED_FIGURES.name)).qs
        self.assertEqual(set(filtered_data), {event_2, event_3})

        # Test events with no recommended figures
        filtered_data = self.filter_class(data=dict(qa_rule=QA_RULE_TYPE.HAS_NO_RECOMMENDED_FIGURES.name)).qs
        self.assertEqual(
            set(filtered_data),
            {
                event_0,
            },
        )

    def test_event_review_status(self):
        e_REVIEW_NOT_STARTED = EventFactory.create(review_status=Event.EVENT_REVIEW_STATUS.REVIEW_NOT_STARTED)
        e_REVIEW_IN_PROGRESS = EventFactory.create(review_status=Event.EVENT_REVIEW_STATUS.REVIEW_IN_PROGRESS)
        e_APPROVED = EventFactory.create(review_status=Event.EVENT_REVIEW_STATUS.APPROVED)
        e_SIGNED_OFF = EventFactory.create(review_status=Event.EVENT_REVIEW_STATUS.SIGNED_OFF)
        e_APPROVED_BUT_CHANGED = EventFactory.create(review_status=Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED)
        e_SIGNED_OFF_BUT_CHANGED = EventFactory.create(review_status=Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED)
        e_all = [
            e_REVIEW_NOT_STARTED,
            e_REVIEW_IN_PROGRESS,
            e_APPROVED,
            e_SIGNED_OFF,
            e_APPROVED_BUT_CHANGED,
            e_SIGNED_OFF_BUT_CHANGED,
        ]

        for filters, expected in [
            # Normal filters
            [
                [Event.EVENT_REVIEW_STATUS.REVIEW_NOT_STARTED],
                [e_REVIEW_NOT_STARTED],
            ],
            [
                [Event.EVENT_REVIEW_STATUS.APPROVED],
                [e_APPROVED],
            ],
            [
                [Event.EVENT_REVIEW_STATUS.SIGNED_OFF],
                [e_SIGNED_OFF],
            ],
            # For this, additional filters are also provided
            [
                [Event.EVENT_REVIEW_STATUS.REVIEW_IN_PROGRESS],
                [e_REVIEW_IN_PROGRESS, e_APPROVED_BUT_CHANGED, e_SIGNED_OFF_BUT_CHANGED],
            ],
            # Above is same as this one
            [
                [
                    Event.EVENT_REVIEW_STATUS.REVIEW_IN_PROGRESS,
                    Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED,
                    Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED,
                ],
                [e_REVIEW_IN_PROGRESS, e_APPROVED_BUT_CHANGED, e_SIGNED_OFF_BUT_CHANGED],
            ],
            # For this, filters are ignore.
            [
                [Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED],
                e_all,
            ],
            [
                [Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED],
                e_all,
            ],
            [
                [Event.EVENT_REVIEW_STATUS.SIGNED_OFF, Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED],
                [e_SIGNED_OFF],
            ],
            [
                [Event.EVENT_REVIEW_STATUS.SIGNED_OFF, Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED],
                [e_SIGNED_OFF],
            ],
        ]:
            # With value - Internal interface
            obtained = self.filter_class(data=dict(review_status=[v.value for v in filters])).qs
            self.assertQuerySetEqual(expected, obtained, filters)
            # With name - GraphQl interface
            obtained = self.filter_class(data=dict(review_status=[v.name for v in filters])).qs
            self.assertQuerySetEqual(expected, obtained, filters)

    def test_event_search_by_event_code_event_code(self):
        asia_event = EventFactory.create(event_type=DISASTER, name="asia-event")
        asia_event_1 = EventFactory.create(event_type=CONFLICT, name="asia-event-1")
        asia_event_2 = EventFactory.create(event_type=DISASTER, name="asia-event-2")

        asia_event_3 = EventFactory.create(event_type=DISASTER, name="asia-event-3")
        EventFactory.create(event_type=DISASTER, name="africa-event")

        EventCodeFactory.create(event_code="nepal-event-code-1", event=asia_event_1)
        EventCodeFactory.create(event_code="nepal-event-code-2", event=asia_event_1)

        EventCodeFactory.create(event_code="india-event-code-1", event=asia_event_2)
        EventCodeFactory.create(event_code="india-event-code-2", event=asia_event_2)

        obtained = self.filter_class(data=dict(search="asia")).qs
        expected = [asia_event, asia_event_1, asia_event_2, asia_event_3]
        self.assertQuerySetEqual(expected, obtained)

        obtained = self.filter_class(data=dict(search="nepal")).qs
        expected = [asia_event_1]
        self.assertQuerySetEqual(expected, obtained)

        obtained = self.filter_class(data=dict(search="asia", event_types=[CONFLICT])).qs
        expected = [asia_event_1]
        self.assertQuerySetEqual(expected, obtained)


class TestEventReviewCountAggregation(HelixTestCase):
    """The review counts must count figures, not the rows a co-annotated join multiplies.

    An aggregate whose filter spans `figures__geo_locations` puts the geolocation join in the outer
    FROM, and Django reuses the `figures` join, so an un-distincted Count over `figures` counts one
    row per (figure, geolocation). The list then sorted on numbers that contradicted the
    `reviewCount` values it rendered, which come from EventReviewCountLoader.

    `filter_qa_rule(HAS_NO_RECOMMENDED_FIGURES)` was the filter that widened the join; it is an
    `Exists` now, so nothing in `EventFilter` widens it and the filter alone proves nothing. The
    widening aggregate is therefore co-annotated here directly, which is what
    `Event.annotate_review_figures_count`'s missing `distinct` is documented as being safe against.
    """

    filter_class = EventFilter

    # 4 figures x 3 geolocations: the row count the `figures` join carries once widened.
    FANOUT_ROWS = 12

    def setUp(self) -> None:
        # ignore_qa=True keeps the event inside the HAS_NO_RECOMMENDED_FIGURES filter (its
        # figure_count stays 0) while the figure below still counts towards the review counts --
        # which is the shape the prod-like data hits: the geolocation join is in the FROM either
        # way, so it multiplies the rows the review counts see.
        self.event = EventFactory.create(ignore_qa=True, include_triangulation_in_qa=False)
        entry = EntryFactory.create()
        # One figure per review status, three geolocations each: every count must stay 1, not
        # become 3. One status per figure is what makes all four counts load-bearing -- with a
        # single figure the other three are 0 either way.
        self.figures = {}
        for status in (
            Figure.FIGURE_REVIEW_STATUS.REVIEW_NOT_STARTED,
            Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS,
            Figure.FIGURE_REVIEW_STATUS.REVIEW_RE_REQUESTED,
            Figure.FIGURE_REVIEW_STATUS.APPROVED,
        ):
            figure = FigureFactory.create(
                entry=entry,
                event=self.event,
                role=Figure.ROLE.RECOMMENDED,
                review_status=status,
                category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            )
            for _ in range(3):
                figure.geo_locations.add(FigureLocationFactory.create())
            self.figures[status] = figure

    KEYS = (
        "review_not_started_count",
        "review_in_progress_count",
        "review_re_request_count",
        "review_approved_count",
        "total_count",
        "progress",
    )

    def _counts(self, **data):
        """The six counts as the list's sort path computes them, with the `figures` join widened.

        `_fanout` is an aggregate over `figures__geo_locations`, so the geolocation join sits in the
        same FROM the review counts aggregate over -- the exact shape a distinct-less Count over
        `figures` triples. It is selected, not merely annotated, so that the join is provably there.
        """
        qs = self.filter_class(data=data, ordering="review_not_started_count").qs
        row = qs.filter(id=self.event.id).annotate(_fanout=Count("figures__geo_locations")).values("_fanout", *self.KEYS)
        row = row.first()
        if row is None:
            return None
        self.assertEqual(row.pop("_fanout"), self.FANOUT_ROWS, "the co-annotated join no longer widens `figures`")
        return row

    def test_every_count_survives_the_qa_rule_join(self):
        for figure in self.figures.values():
            self.assertEqual(figure.geo_locations.count(), 3)
        counts = self._counts(qa_rule=QA_RULE_TYPE.HAS_NO_RECOMMENDED_FIGURES.name)
        self.assertIsNotNone(counts, "the event dropped out of the qa_rule filter")
        self.assertEqual(
            counts,
            {
                "review_not_started_count": 1,
                "review_in_progress_count": 1,
                "review_re_request_count": 1,
                "review_approved_count": 1,
                "total_count": 4,
                "progress": 0.25,
            },
        )

    def test_progress_is_a_fraction_not_an_integer_division(self):
        """1 approved of 4 is 0.25; an integer division truncates every partial row to 0."""
        counts = self._counts()
        self.assertAlmostEqual(counts["progress"], 0.25, places=4)

    def test_the_count_agrees_with_the_unfiltered_list(self):
        self.assertEqual(
            self._counts(qa_rule=QA_RULE_TYPE.HAS_NO_RECOMMENDED_FIGURES.name),
            self._counts(),
        )

    def test_every_review_count_key_is_orderable(self):
        """The six keys feed one client table; allowlisting only some breaks the others.

        `progress` was allowlisted and the other five were not, so sorting the QA table by any
        of them hard-errored while the values were rendered normally.
        """
        for key in Event.annotate_review_figures_count():
            with self.subTest(key=key):
                self.assertIn(key, Event.ORDERING_ALLOWLIST)
                qs = nulls_last_order_queryset(self.filter_class(data={}, ordering=key).qs, "ordering", ordering=key)
                self.assertEqual([event.id for event in qs], [self.event.id])


class TestEventSortAnnotationsMatchAPythonRecount(HelixTestCase):
    """The sort-path annotations are CTEs LEFT-JOINed by event id, so their edge cases are
    structural: an event with no figures gets no CTE row at all, and the review counts' second
    OR arm reads `include_triangulation_in_qa` off the EVENT, not off the figure.

    Every value is checked against a recount done in Python over the same figures, so a CTE that
    groups or joins wrongly cannot agree with it.
    """

    filter_class = EventFilter

    def setUp(self) -> None:
        self.entry = EntryFactory.create()
        self.other_entry = EntryFactory.create()

        # Triangulation counts towards QA here, so a non-RECOMMENDED figure still counts.
        self.triangulated = EventFactory.create(include_triangulation_in_qa=True)
        self._figure(self.triangulated, self.entry, Figure.ROLE.RECOMMENDED, Figure.FIGURE_REVIEW_STATUS.REVIEW_NOT_STARTED)
        self._figure(
            self.triangulated, self.entry, Figure.ROLE.TRIANGULATION, Figure.FIGURE_REVIEW_STATUS.REVIEW_NOT_STARTED
        )
        self._figure(self.triangulated, self.other_entry, Figure.ROLE.TRIANGULATION, Figure.FIGURE_REVIEW_STATUS.APPROVED)

        # Triangulation excluded, so only the RECOMMENDED figure counts.
        self.recommended_only = EventFactory.create(include_triangulation_in_qa=False)
        self._figure(self.recommended_only, self.entry, Figure.ROLE.RECOMMENDED, Figure.FIGURE_REVIEW_STATUS.APPROVED)
        self._figure(
            self.recommended_only, self.entry, Figure.ROLE.TRIANGULATION, Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS
        )

        self.figureless = EventFactory.create(include_triangulation_in_qa=True)

    def _figure(self, event, entry, role, review_status):
        return FigureFactory.create(
            entry=entry,
            event=event,
            role=role,
            review_status=review_status,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
        )

    def _annotated(self, ordering, keys):
        qs = self.filter_class(data={}, ordering=ordering).qs
        return {row["id"]: row for row in qs.values("id", *keys)}

    def _python_review_counts(self, event):
        figures = list(event.figures.all())
        counts = {
            name: sum(
                1
                for figure in figures
                if figure.review_status == status
                and (figure.role == Figure.ROLE.RECOMMENDED or event.include_triangulation_in_qa)
            )
            for name, status in Event.REVIEW_FIGURE_COUNT_STATUSES.items()
        }
        total = sum(counts.values())
        return {
            **counts,
            "total_count": total,
            "progress": counts["review_approved_count"] / total if total else 0.0,
        }

    def test_review_counts_equal_the_python_recount(self):
        keys = sorted(Event.REVIEW_FIGURES_COUNT_ANNOTATIONS)
        annotated = self._annotated("review_not_started_count", keys)
        for event in (self.triangulated, self.recommended_only, self.figureless):
            with self.subTest(event=event.id, triangulation=event.include_triangulation_in_qa):
                self.assertEqual(annotated[event.id], {"id": event.id, **self._python_review_counts(event)})

    def test_review_counts_of_the_spelt_out_fixture(self):
        """The recount and the CTE could only agree on wrong numbers if both read the fixture the
        same wrong way, so the three shapes are also pinned literally."""
        annotated = self._annotated("review_not_started_count", sorted(Event.REVIEW_FIGURES_COUNT_ANNOTATIONS))
        # 2 not-started (one RECOMMENDED, one TRIANGULATION) + 1 approved TRIANGULATION.
        self.assertEqual(
            annotated[self.triangulated.id],
            {
                "id": self.triangulated.id,
                "review_not_started_count": 2,
                "review_in_progress_count": 0,
                "review_re_request_count": 0,
                "review_approved_count": 1,
                "total_count": 3,
                "progress": 1 / 3,
            },
        )
        # The in-progress TRIANGULATION figure is invisible without the event's opt-in.
        self.assertEqual(
            annotated[self.recommended_only.id],
            {
                "id": self.recommended_only.id,
                "review_not_started_count": 0,
                "review_in_progress_count": 0,
                "review_re_request_count": 0,
                "review_approved_count": 1,
                "total_count": 1,
                "progress": 1.0,
            },
        )
        # No CTE row: every count coalesces to 0, and progress divides nothing.
        self.assertEqual(
            annotated[self.figureless.id],
            {
                "id": self.figureless.id,
                "review_not_started_count": 0,
                "review_in_progress_count": 0,
                "review_re_request_count": 0,
                "review_approved_count": 0,
                "total_count": 0,
                "progress": 0.0,
            },
        )

    def test_the_sort_path_and_the_dataloader_path_agree(self):
        """`EventReviewCountLoader` keeps the id-scoped aggregate; the list sorts on the CTE. The
        two must not disagree, or the table sorts on numbers it does not render.

        Each is checked against the Python recount rather than against the other: comparing the two
        shapes alone is satisfied by using one shape for both, which is exactly the confusion this
        test exists to catch.
        """
        keys = sorted(Event.REVIEW_FIGURES_COUNT_ANNOTATIONS)
        expected = {
            event.id: {"id": event.id, **self._python_review_counts(event)}
            for event in (self.triangulated, self.recommended_only, self.figureless)
        }
        from_cte = self._annotated("review_not_started_count", keys)
        from_aggregate = {
            row["id"]: row for row in Event.objects.annotate(**Event.annotate_review_figures_count()).values("id", *keys)
        }
        self.assertEqual(from_aggregate, expected)
        self.assertEqual(from_cte, expected)

    def test_entry_count_counts_distinct_entries_and_leaves_figureless_events_null(self):
        annotated = self._annotated("entry_count", ["entry_count"])
        for event in (self.triangulated, self.recommended_only, self.figureless):
            entries = {figure.entry_id for figure in event.figures.all()}
            with self.subTest(event=event.id):
                self.assertEqual(annotated[event.id]["entry_count"], len(entries) or None)
        # Two figures share an entry on this event: 3 figures, 2 entries.
        self.assertEqual(self.triangulated.figures.count(), 3)
        self.assertEqual(annotated[self.triangulated.id]["entry_count"], 2)
        self.assertIsNone(annotated[self.figureless.id]["entry_count"])

    def test_every_denormalised_sort_key_composes_in_one_query(self):
        """Each sort key adds its own CTE to the same queryset; ordering by several at once must
        still compile and return every event exactly once."""
        ordering = "entry_count,-review_approved_count,total_stock_idp_figures,countries__idmc_short_name"
        qs = nulls_last_order_queryset(self.filter_class(data={}, ordering=ordering).qs, "ordering", ordering=ordering)
        ids = [event.id for event in qs]
        self.assertEqual(sorted(ids), sorted(Event.objects.values_list("id", flat=True)))
