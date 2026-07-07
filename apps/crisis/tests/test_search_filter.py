from apps.crisis.filters import CrisisFilter
from apps.crisis.models import Crisis
from utils.factories import CrisisFactory, EventFactory
from utils.tests import HelixTestCase

DISASTER = Crisis.CRISIS_TYPE.DISASTER


class TestMultiWordSearchFilter(HelixTestCase):
    """Multi-word search through `CrisisFilter` (fields: name + events__name):
    bilateral accent folding, record-level term matching, and input guards."""

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

    # -- Regression 2: record-level multi-word matching over a to-many field --

    def test_multi_word_same_event_matches(self):
        # Both words live in the SAME single event name -> the crisis matches.
        # A crisis whose lone event holds only ONE of the words must NOT match
        # (every term must narrow the result set).
        crisis = CrisisFactory.create(crisis_type=DISASTER, name="alpha")
        EventFactory.create(name="Karnali Lumbini Flood", crisis=crisis)

        other = CrisisFactory.create(crisis_type=DISASTER, name="beta")
        EventFactory.create(name="Karnali Flood", crisis=other)

        obtained = self.filter_class(data=dict(search="karnali lumbini")).qs
        self.assertQuerySetEqual([crisis], obtained)

    def test_multi_word_split_across_events_matches(self):
        # The two words are split across TWO DIFFERENT events of the same crisis:
        # record-level semantics -> the crisis matches, exactly once (no join
        # fan-out duplicates).
        split_crisis = CrisisFactory.create(crisis_type=DISASTER, name="gamma")
        EventFactory.create(name="Karnali Flood", crisis=split_crisis)
        EventFactory.create(name="Lumbini Drought", crisis=split_crisis)

        obtained = self.filter_class(data=dict(search="karnali lumbini")).qs
        self.assertQuerySetEqual([split_crisis], obtained)

    def test_multi_word_split_across_parent_and_event_matches(self):
        # One word on the crisis itself, the other on one of its events.
        crisis = CrisisFactory.create(crisis_type=DISASTER, name="Karnali basin")
        EventFactory.create(name="Lumbini Drought", crisis=crisis)

        # Control: holds only one of the words across all its fields.
        other = CrisisFactory.create(crisis_type=DISASTER, name="Karnali delta")
        EventFactory.create(name="Bagmati Flood", crisis=other)

        obtained = self.filter_class(data=dict(search="karnali lumbini")).qs
        self.assertQuerySetEqual([crisis], obtained)

    def test_multi_word_on_parent_without_children_matches(self):
        # Both words on the crisis itself, NO events at all: the correlated Exists
        # branch is empty but the parent-field branch must still match.
        crisis = CrisisFactory.create(crisis_type=DISASTER, name="Karnali Lumbini appeal")

        obtained = self.filter_class(data=dict(search="karnali lumbini")).qs
        self.assertQuerySetEqual([crisis], obtained)

    def test_record_level_truth_table(self):
        # Every term must match SOMEWHERE on the record (crisis name or any event
        # name); a single unmatched term excludes the crisis.
        crisis = CrisisFactory.create(crisis_type=DISASTER, name="Nepal Earthquake")
        EventFactory.create(name="Kathmandu Earthquake", crisis=crisis)
        EventFactory.create(name="Pokhara Earthquake", crisis=crisis)

        matching_searches = [
            "earthquake",
            "nepal",
            "kathmandu",
            "pokhara",
            "nepal kathmandu",
            "nepal pokhara",
            "nepal kathmandu pokhara",
        ]
        non_matching_searches = [
            "india",
            "imadol",
            "kathmandu imadol",
            "pokhara gandaki",
            "flood",
        ]
        for search in matching_searches:
            with self.subTest(search=search, expected="match"):
                self.assertQuerySetEqual([crisis], self.filter_class(data=dict(search=search)).qs)
        for search in non_matching_searches:
            with self.subTest(search=search, expected="no match"):
                self.assertQuerySetEqual([], self.filter_class(data=dict(search=search)).qs)

    # -- Input guards: normalization edge cases and abuse limits --

    def test_search_with_no_surviving_terms_is_a_no_op(self):
        # Punctuation-only input (and 1-char-only input) normalizes to zero usable
        # terms: the search must behave like search="" — no filtering — instead of
        # silently matching nothing or everything through an empty condition.
        crises = CrisisFactory.create_batch(2, crisis_type=DISASTER)

        for search in ["!!!", "...", "?", "u s a"]:
            with self.subTest(search=search):
                self.assertQuerySetEqual(crises, self.filter_class(data=dict(search=search)).qs)

    def test_single_character_terms_are_dropped(self):
        # "s flood" behaves as "flood": the 1-char noise term must not exclude a
        # record that the meaningful term matches.
        crisis = CrisisFactory.create(crisis_type=DISASTER, name="Karnali Flood")
        CrisisFactory.create(crisis_type=DISASTER, name="Bagmati Drought")

        obtained = self.filter_class(data=dict(search="s flood")).qs
        self.assertQuerySetEqual([crisis], obtained)

    def test_search_length_is_capped(self):
        # Characters beyond SEARCH_MAX_LENGTH are ignored: a non-matching term
        # placed past the cap must not exclude the record.
        crisis = CrisisFactory.create(crisis_type=DISASTER, name="Karnali Flood")

        search = "flood".ljust(self.filter_class.SEARCH_MAX_LENGTH) + "zzznomatch"
        obtained = self.filter_class(data=dict(search=search)).qs
        self.assertQuerySetEqual([crisis], obtained)

    def test_term_count_is_capped(self):
        # Only the first SEARCH_MAX_TERMS terms filter: the term after the cap
        # (non-matching) must be ignored.
        words = [f"wd{index:02d}" for index in range(self.filter_class.SEARCH_MAX_TERMS)]
        crisis = CrisisFactory.create(crisis_type=DISASTER, name=" ".join(words))

        obtained = self.filter_class(data=dict(search=" ".join(words + ["zzznomatch"]))).qs
        self.assertQuerySetEqual([crisis], obtained)

    def test_bare_relation_search_path_fails_loudly(self):
        # A path that names a relation but no column is a misconfiguration.
        from apps.event.models import Event

        filterset = self.filter_class(data=dict(search="x"))
        with self.assertRaises(NotImplementedError):
            filterset.to_many_exists(Event, "event_code", {"helix_unaccent__icontains": "x"})

    def test_to_one_first_search_path_is_not_implemented(self):
        # A path whose FIRST hop is to-one (e.g. event -> crisis__countries__name)
        # has a correct-but-unused self-join form, kept commented out in
        # to_many_exists until a real use case enables it with tests.
        from apps.event.models import Event

        filterset = self.filter_class(data=dict(search="x"))
        with self.assertRaises(NotImplementedError):
            filterset.to_many_exists(Event, "crisis__countries__name", {"helix_unaccent__icontains": "x"})
