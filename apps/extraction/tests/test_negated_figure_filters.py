from apps.crisis.models import Crisis
from apps.extraction.filters import EntryExtractionFilterSet
from utils.factories import (
    DisasterCategoryFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
)
from utils.tests import HelixTestCase

CONFLICT = Crisis.CRISIS_TYPE.CONFLICT
DISASTER = Crisis.CRISIS_TYPE.DISASTER


class TestNegatedDisasterCategoryFilter(HelixTestCase):
    """`filter_figure_disaster_categories` must keep the baseline truth table.

    An entry is KEPT when it has NO disaster figure at all, OR has a disaster figure in one
    of the requested categories — i.e. the baseline
    ``~Q(figures__figure_cause=DISASTER) | Q(figures__disaster_category__in=value)``,
    compiled as ``~Exists(disaster figure) | Exists(matching figure)``.

    Regression guard: collapsing this into a single ``Exists(~Q | Q)`` flips the table —
    it drops figureless entries and admits an entry via any *non*-matching figure. The four
    entries below are the four rows of that table; the filter is run for the "Flood" category.
    """

    @classmethod
    def setUpTestData(cls):
        # We filter for "Flood"; "Earthquake" is an unrelated disaster category.
        cls.flood = DisasterCategoryFactory.create(name="Flood")
        cls.earthquake = DisasterCategoryFactory.create(name="Earthquake")
        # Figure.event is NOT NULL; the filter keys off figure_cause / disaster_category
        # (not the event), so one shared event is enough.
        cls.event = EventFactory.create()

        # KEPT — only a conflict figure, no disaster figure (the ~Exists(disaster) leg).
        cls.conflict_only_entry = cls._entry("conflict-only")
        cls._conflict_figure(cls.conflict_only_entry)

        # DROPPED — its only disaster figure is in a different category (Earthquake).
        cls.other_category_entry = cls._entry("earthquake-only")
        cls._disaster_figure(cls.other_category_entry, cls.earthquake)

        # KEPT — has a disaster figure in the requested category (Flood).
        cls.matching_entry = cls._entry("flood")
        cls._disaster_figure(cls.matching_entry, cls.flood)

        # KEPT — no figures at all (the regression specifically dropped figureless entries).
        cls.figureless_entry = cls._entry("figureless")

    # --- data builders ---------------------------------------------------
    @staticmethod
    def _entry(title):
        return EntryFactory.create(article_title=title)

    @classmethod
    def _conflict_figure(cls, entry):
        return FigureFactory.create(
            entry=entry,
            event=cls.event,
            figure_cause=CONFLICT,
            disaster_category=None,
        )

    @classmethod
    def _disaster_figure(cls, entry, category):
        return FigureFactory.create(
            entry=entry,
            event=cls.event,
            figure_cause=DISASTER,
            disaster_category=category,
        )

    def _entry_ids_for_disaster_categories(self, *categories):
        """Run filter_figure_disaster_categories for `categories`; return matching entry ids.

        Builds ``filter_figure_disaster_categories=[<category ids>]`` (empty when no categories
        are given), runs the extraction filterset, and returns the resulting entry id set.
        """
        value = [category.pk for category in categories]
        qs = EntryExtractionFilterSet(data={"filter_figure_disaster_categories": value}).qs
        return set(qs.values_list("id", flat=True))

    # --- tests -----------------------------------------------------------
    def test_matches_baseline_truth_table(self):
        kept = self._entry_ids_for_disaster_categories(self.flood)
        self.assertEqual(
            kept,
            {
                self.conflict_only_entry.id,  # no disaster figure
                self.matching_entry.id,  # disaster figure in Flood
                self.figureless_entry.id,  # no figures
            },
            "filter_figure_disaster_categories diverged from the baseline row set",
        )
        # the lone exclusion: an entry whose only disaster figure is a different category
        self.assertNotIn(self.other_category_entry.id, kept)

    def test_figureless_entry_is_kept(self):
        # The regression dropped figureless entries — assert it survives.
        self.assertIn(
            self.figureless_entry.id,
            self._entry_ids_for_disaster_categories(self.flood),
        )

    def test_entry_with_only_a_different_category_disaster_figure_is_excluded(self):
        self.assertNotIn(
            self.other_category_entry.id,
            self._entry_ids_for_disaster_categories(self.flood),
        )

    def test_entry_with_both_matching_and_nonmatching_figures_is_kept(self):
        # Exists(matching) admits the entry even when a non-matching disaster figure is present.
        entry = self._entry("flood-and-earthquake")
        self._disaster_figure(entry, self.earthquake)
        self._disaster_figure(entry, self.flood)
        self.assertIn(entry.id, self._entry_ids_for_disaster_categories(self.flood))

    def test_empty_value_returns_all_entries(self):
        # No categories -> empty filter value -> unfiltered queryset (all four entries).
        self.assertEqual(
            self._entry_ids_for_disaster_categories(),
            {
                self.conflict_only_entry.id,
                self.other_category_entry.id,
                self.matching_entry.id,
                self.figureless_entry.id,
            },
        )
