from datetime import date

from django.test import TestCase

from apps.country.dataloaders import CountryTotalFigureDisaggregationLoader
from apps.country.models import Country
from apps.crisis.dataloaders import CrisisTotalFigureDisaggregationLoader
from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.event.dataloaders import EventTotalFigureDisaggregationLoader
from apps.event.models import Event
from utils.factories import (
    CrisisFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
)

# The event/crisis consolidated loaders have no year scope: ND sums every
# NEW_DISPLACEMENT/RECOMMENDED figure, and IDP sums the IDPS/RECOMMENDED figures whose end_date
# equals the parent's MAX(end_date) over its IDPS/RECOMMENDED figures. One IDPS figure per parent
# makes that reference date its own end_date.
FLOW_END = date(2022, 3, 10)
STOCK_END = date(2022, 12, 31)

# All four totals differ, so a value landing on the wrong key or the wrong field is visible.
FIRST_ND = 11
FIRST_IDP = 33
SECOND_ND = 55
SECOND_IDP = 77


class DisaggregationLoaderKeyOrderTestCase(TestCase):
    """A batch's values are positional: value i belongs to keys[i].

    `EventTotalFigureDisaggregationLoader` and `CrisisTotalFigureDisaggregationLoader` build one
    grouped CTE per batch and index the rows by id, so nothing about the queryset's own row order
    or a key with no matching figures may shift the list.

    Asymmetry pinned here on purpose: `apps.country.dataloaders` substitutes a fully-populated
    dict of `None`s for a key its queryset did not return, while `apps.event.dataloaders` and
    `apps.crisis.dataloaders` hand back a bare `None` (their resolvers guard it). A reader of one
    module must not assume the other's shape.
    """

    @classmethod
    def setUpTestData(cls):
        entry = EntryFactory.create()

        cls.first_crisis = CrisisFactory.create(crisis_type=Crisis.CRISIS_TYPE.CONFLICT)
        cls.second_crisis = CrisisFactory.create(crisis_type=Crisis.CRISIS_TYPE.CONFLICT)
        # One event per crisis, so an event total and its crisis total are the same number and a
        # crossed key is unambiguous.
        cls.first_event = EventFactory.create(crisis=cls.first_crisis)
        cls.second_event = EventFactory.create(crisis=cls.second_crisis)

        for event, nd_total, idp_total in (
            (cls.first_event, FIRST_ND, FIRST_IDP),
            (cls.second_event, SECOND_ND, SECOND_IDP),
        ):
            FigureFactory.create(
                entry=entry,
                event=event,
                category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                role=Figure.ROLE.RECOMMENDED,
                total_figures=nd_total,
                start_date=date(2022, 1, 10),
                end_date=FLOW_END,
            )
            FigureFactory.create(
                entry=entry,
                event=event,
                category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
                role=Figure.ROLE.RECOMMENDED,
                total_figures=idp_total,
                start_date=date(2022, 1, 10),
                end_date=STOCK_END,
            )

    def test_event_loader_values_follow_key_order_and_a_missing_key_holds_its_place(self) -> None:
        # No such event: the sum of two existing ids cannot collide with either.
        missing = self.first_event.id + self.second_event.id
        keys = [self.second_event.id, missing, self.first_event.id]

        values = EventTotalFigureDisaggregationLoader().batch_load_fn(keys).get()

        self.assertEqual(len(values), len(keys))
        self.assertEqual(
            values[0],
            {
                "id": self.second_event.id,
                Event.ND_FIGURES_ANNOTATE: SECOND_ND,
                Event.IDP_FIGURES_ANNOTATE: SECOND_IDP,
            },
        )
        # The event loader returns a bare None here; the resolvers guard it.
        self.assertIsNone(values[1])
        self.assertEqual(
            values[2],
            {
                "id": self.first_event.id,
                Event.ND_FIGURES_ANNOTATE: FIRST_ND,
                Event.IDP_FIGURES_ANNOTATE: FIRST_IDP,
            },
        )

    def test_crisis_loader_values_follow_key_order_and_a_missing_key_holds_its_place(self) -> None:
        missing = self.first_crisis.id + self.second_crisis.id
        keys = [self.second_crisis.id, missing, self.first_crisis.id]

        values = CrisisTotalFigureDisaggregationLoader().batch_load_fn(keys).get()

        self.assertEqual(len(values), len(keys))
        self.assertEqual(
            values[0],
            {
                "id": self.second_crisis.id,
                Crisis.ND_FIGURES_ANNOTATE: SECOND_ND,
                Crisis.IDP_FIGURES_ANNOTATE: SECOND_IDP,
            },
        )
        self.assertIsNone(values[1])
        self.assertEqual(
            values[2],
            {
                "id": self.first_crisis.id,
                Crisis.ND_FIGURES_ANNOTATE: FIRST_ND,
                Crisis.IDP_FIGURES_ANNOTATE: FIRST_IDP,
            },
        )

    def test_a_parent_with_no_figures_reports_null_totals_not_a_missing_key(self) -> None:
        # The CTE joins onto the PARENT queryset, so a parent that exists always gets a row --
        # with null totals when it has no figures. Only a key that matches no row at all comes
        # back as None (covered above). Both shapes resolve to null for the client, because the
        # resolvers read `row[...] if row else None` and a dict of Nones is truthy.
        childless_event = EventFactory.create(crisis=CrisisFactory.create())

        event_values = EventTotalFigureDisaggregationLoader().batch_load_fn([childless_event.id]).get()
        assert event_values == [
            {
                "id": childless_event.id,
                Event.ND_FIGURES_ANNOTATE: None,
                Event.IDP_FIGURES_ANNOTATE: None,
            }
        ]

        crisis_values = CrisisTotalFigureDisaggregationLoader().batch_load_fn([childless_event.crisis_id]).get()
        assert crisis_values == [
            {
                "id": childless_event.crisis_id,
                Crisis.ND_FIGURES_ANNOTATE: None,
                Crisis.IDP_FIGURES_ANNOTATE: None,
            }
        ]

    def test_the_country_loader_fills_a_missing_key_where_these_two_do_not(self) -> None:
        # The asymmetry, side by side, so a change to either module trips this test rather than
        # a caller in production.
        absent_id = 10**9  # no row carries it, so each loader takes its missing-key path

        country_values = CountryTotalFigureDisaggregationLoader().batch_load_fn([absent_id]).get()
        event_values = EventTotalFigureDisaggregationLoader().batch_load_fn([absent_id]).get()

        self.assertEqual(
            country_values,
            [
                {
                    Country.ND_CONFLICT_ANNOTATE: None,
                    Country.ND_DISASTER_ANNOTATE: None,
                    Country.IDP_CONFLICT_ANNOTATE: None,
                    Country.IDP_DISASTER_ANNOTATE: None,
                }
            ],
        )
        self.assertEqual(event_values, [None])
