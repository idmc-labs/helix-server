from apps.crisis.filters import CrisisFilter
from apps.crisis.models import Crisis
from utils.factories import CrisisFactory, EventFactory
from utils.tests import HelixTestCase

DISASTER = Crisis.CRISIS_TYPE.DISASTER


class TestMultiWordSearchFilter(HelixTestCase):
    """Regression guards for ``utils.filters.MultiWordSearchFilterSet`` exercised through
    ``CrisisFilter`` (multi_word_search_fields = ["name", "events__name"]).

    Two bugs are guarded:

    1. BILATERAL UNACCENT: ``helix_unaccent`` must fold accents on BOTH the stored
       column and the search term. A one-sided transform made an accented search term
       miss unaccented data (and vice-versa), silently returning 0 rows.

    2. MULTI-WORD SAME-ROW over a to-many field (``events__name``): two words that both
       live in ONE event name must match the crisis; the same two words split across two
       DIFFERENT events of the same crisis must NOT match (a per-term ``Exists`` form
       over-matched by letting terms hit different child rows).
    """

    def setUp(self) -> None:
        self.filter_class = CrisisFilter

    # -- Regression 1: bilateral accent folding on a scalar field (Crisis.name) --

    def test_accented_search_term_matches_unaccented_data(self):
        # Stored data has NO accent; the search term DOES. With a bilateral transform
        # the accent on the term is folded too, so it still matches.
        target = CrisisFactory.create(crisis_type=DISASTER, name="Mexico City")
        CrisisFactory.create(crisis_type=DISASTER, name="Bogota")

        obtained = self.filter_class(data=dict(search="méxico")).qs
        self.assertQuerySetEqual([target], obtained)

    def test_unaccented_search_term_matches_accented_data(self):
        # Mirror direction: stored data HAS an accent, the search term does not.
        target = CrisisFactory.create(crisis_type=DISASTER, name="Córdoba")
        CrisisFactory.create(crisis_type=DISASTER, name="Sevilla")

        obtained = self.filter_class(data=dict(search="cordoba")).qs
        self.assertQuerySetEqual([target], obtained)

    # -- Regression 2: multi-word same-row semantics over a to-many field --

    def test_multi_word_same_event_matches(self):
        # Both words live in the SAME single event name -> the crisis matches.
        # Crisis name is neutral so the match must come from the one event row.
        crisis = CrisisFactory.create(crisis_type=DISASTER, name="alpha")
        EventFactory.create(name="Karnali Lumbini Flood", crisis=crisis)

        # A second crisis whose lone event holds only ONE of the words.
        other = CrisisFactory.create(crisis_type=DISASTER, name="beta")
        EventFactory.create(name="Karnali Flood", crisis=other)

        obtained = self.filter_class(data=dict(search="karnali lumbini")).qs
        self.assertQuerySetEqual([crisis], obtained)

    def test_multi_word_split_across_events_does_not_match(self):
        # The two words are split across TWO DIFFERENT events of the same crisis.
        # Same-row semantics require both terms within ONE joined event row, so this
        # crisis must NOT match. (The broadened per-term Exists form over-matched here.)
        split_crisis = CrisisFactory.create(crisis_type=DISASTER, name="gamma")
        EventFactory.create(name="Karnali Flood", crisis=split_crisis)
        EventFactory.create(name="Lumbini Drought", crisis=split_crisis)

        # A control crisis whose single event holds both words -> the only valid match.
        match_crisis = CrisisFactory.create(crisis_type=DISASTER, name="delta")
        EventFactory.create(name="Karnali Lumbini Storm", crisis=match_crisis)

        obtained = self.filter_class(data=dict(search="karnali lumbini")).qs
        self.assertQuerySetEqual([match_crisis], obtained)
