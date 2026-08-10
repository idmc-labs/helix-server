"""The rendered geolocations string and the geolocations sort key are different values.

`FigureType.geolocations` is rendered by `FigureGeoLocationLoader`
(apps/entry/dataloaders.py) as a concatenation, and `StringAgg` without `ordering=` emits its
inputs in whatever order the plan produces, so the SAME figure's string could differ between
runs. That aggregate must stay ordered.

The `figure_geolocations_agg` CTE in `FigureExtractionFilterSet.qs`
(apps/extraction/filters.py) is a SORT KEY only -- the explicit `resolve_geolocations`
resolver means the annotation never reaches a response. It ranks a figure by its smallest
location name ascending and its greatest descending, which is what ordering by a to-many path
means; a concatenation would rank descending sorts by the smallest name reversed.
"""

from apps.common.utils import EXTERNAL_ARRAY_SEPARATOR
from apps.entry.dataloaders import FigureGeoLocationLoader
from apps.entry.models import Figure
from apps.extraction.filters import FigureExtractionFilterSet
from utils.factories import EventFactory, FigureFactory, FigureLocationFactory
from utils.tests import HelixTestCase

# Attached in reverse-alphabetical order on purpose: an unordered aggregate follows the scan
# order of the through table, which on a freshly built test table is insertion order -- i.e.
# the exact reverse of what an ordered aggregate must produce. Five of them, so a spurious
# pass would need the planner to sort by accident.
NAMES_IN_ATTACH_ORDER = ["zulu town", "yankee city", "x-ray village", "whiskey ward", "victor valley"]
EXPECTED = EXTERNAL_ARRAY_SEPARATOR.join(sorted(NAMES_IN_ATTACH_ORDER))


class TestGeolocationAggregateOrdering(HelixTestCase):
    @classmethod
    def setUpTestData(cls):
        event = EventFactory.create()
        cls.figure = FigureFactory.create(event=event, role=Figure.ROLE.RECOMMENDED)
        for name in NAMES_IN_ATTACH_ORDER:
            cls.figure.geo_locations.add(FigureLocationFactory.create(display_name=name))
        # A second figure with one location: proves the grouping still holds and that the
        # ordering is per figure, not global.
        cls.other = FigureFactory.create(event=event, role=Figure.ROLE.RECOMMENDED)
        cls.other.geo_locations.add(FigureLocationFactory.create(display_name="alpha town"))

    def _sort_keys(self, ordering):
        return dict(FigureExtractionFilterSet(data={}, ordering=ordering).qs.values_list("id", "geolocations"))

    def test_loader_concatenates_display_names_alphabetically(self):
        loaded = FigureGeoLocationLoader().batch_load_fn([self.figure.id, self.other.id]).get()
        self.assertEqual(loaded[0], EXPECTED)
        self.assertEqual(loaded[1], "alpha town")

    def test_sort_key_is_the_smallest_location_name_ascending(self):
        rows = self._sort_keys("geolocations")
        self.assertEqual(rows[self.figure.id], min(NAMES_IN_ATTACH_ORDER))
        self.assertEqual(rows[self.other.id], "alpha town")

    def test_sort_key_is_the_greatest_location_name_descending(self):
        rows = self._sort_keys("-geolocations")
        self.assertEqual(rows[self.figure.id], max(NAMES_IN_ATTACH_ORDER))
        self.assertEqual(rows[self.other.id], "alpha town")

    def test_the_sort_key_is_not_the_rendered_string(self):
        """They answer different questions, so they are deliberately not equal.

        The rendered value lists every location; the sort key is the one name the figure ranks
        at. Asserting they agree is what allowed a concatenation to stand in as a sort key.
        """
        loaded = FigureGeoLocationLoader().batch_load_fn([self.figure.id]).get()
        self.assertEqual(loaded[0], EXPECTED)
        self.assertNotEqual(self._sort_keys("geolocations")[self.figure.id], EXPECTED)
