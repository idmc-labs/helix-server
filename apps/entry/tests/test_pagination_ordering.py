from apps.entry.models import Figure
from utils.factories import CountryFactory, EntryFactory, EventFactory, FigureFactory
from utils.graphene.pagination import nulls_last_order_queryset
from utils.tests import HelixTestCase


class TestEmptyOrderingFallback(HelixTestCase):
    """Paginating with no requested ordering must not slice plan-dependent physical
    order — nulls_last_order_queryset falls back to newest-first pk, but respects a
    queryset that already carries an ordering."""

    def setUp(self) -> None:
        country = CountryFactory.create()
        event = EventFactory.create()
        entry = EntryFactory.create()
        self.figs = FigureFactory.create_batch(3, entry=entry, event=event, country=country)

    def test_unordered_queryset_falls_back_to_pk_asc(self):
        # ascending pk: deterministic AND preserves the de-facto insertion order
        # unordered lists (e.g. the public GIDD endpoints) have always returned
        qs = nulls_last_order_queryset(Figure.objects.all(), "ordering")
        self.assertTrue(qs.ordered)
        self.assertEqual([f.id for f in qs], sorted(f.id for f in self.figs))

    def test_already_ordered_queryset_is_respected(self):
        qs = nulls_last_order_queryset(Figure.objects.order_by("-id"), "ordering")
        self.assertEqual(
            [f.id for f in qs],
            sorted((f.id for f in self.figs), reverse=True),
        )

    def test_explicit_ordering_still_applies(self):
        qs = nulls_last_order_queryset(Figure.objects.all(), "ordering", ordering="-id")
        self.assertEqual(
            [f.id for f in qs],
            sorted((f.id for f in self.figs), reverse=True),
        )
