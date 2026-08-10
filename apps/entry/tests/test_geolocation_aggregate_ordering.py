"""The geolocations aggregate must concatenate in a declared order.

`StringAgg` without `ordering=` emits its inputs in whatever order the plan produces them,
so the SAME figure's `geolocations` string can differ between two runs, between two
deployments, or after an index changes the chosen plan. That is a response value the client
renders.

Two independent aggregates build this string and both must stay ordered:
  * `FigureGeoLocationLoader` (apps/entry/dataloaders.py) -> `FigureType.geolocations`
  * the `figure_geolocations_agg` CTE in `FigureExtractionFilterSet.qs`
    (apps/extraction/filters.py) -> the `geolocations` SORT KEY
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

    def _sort_keys(self):
        return dict(FigureExtractionFilterSet(data={}, ordering="geolocations").qs.values_list("id", "geolocations"))

    def test_loader_concatenates_display_names_alphabetically(self):
        loaded = FigureGeoLocationLoader().batch_load_fn([self.figure.id, self.other.id]).get()
        self.assertEqual(loaded[0], EXPECTED)
        self.assertEqual(loaded[1], "alpha town")

    def test_sort_key_concatenates_display_names_alphabetically(self):
        rows = self._sort_keys()
        self.assertEqual(rows[self.figure.id], EXPECTED)
        self.assertEqual(rows[self.other.id], "alpha town")

    def test_the_two_aggregates_agree(self):
        """The sort key and the rendered value are built by different code.

        A client sorting on `geolocations` and reading `geolocations` must not see the list
        ordered by a string it is never shown.
        """
        loaded = FigureGeoLocationLoader().batch_load_fn([self.figure.id, self.other.id]).get()
        rows = self._sort_keys()
        self.assertEqual(loaded[0], rows[self.figure.id])
        self.assertEqual(loaded[1], rows[self.other.id])
