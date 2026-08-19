from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext

from utils.factories import CountryFactory, EventFactory, ReportFactory
from utils.tests import HelixTestCase


class TestGetFilterKwargsCache(HelixTestCase):
    """QueryAbstractModel.get_filter_kwargs is cached keyed (model, pk, modified_at):
    a cache hit must not re-read the ~18 filter M2M relations, and any save (every
    serializer/admin edit path saves before setting M2Ms) must rotate the key."""

    def setUp(self) -> None:
        cache.clear()
        self.countries = CountryFactory.create_batch(2)
        self.event = EventFactory.create()
        self.report = ReportFactory.create()
        self.report.filter_figure_countries.set(self.countries)
        self.report.filter_figure_events.set([self.event])
        # the .set() calls above do not bump modified_at; refresh + save to start clean
        self.report.save()

    def test_second_read_hits_cache_with_zero_queries(self):
        first = self.report.get_filter_kwargs
        with CaptureQueriesContext(connection) as ctx:
            second = self.report.get_filter_kwargs
        self.assertEqual(len(ctx.captured_queries), 0)
        self.assertEqual(first, second)
        self.assertEqual(
            sorted(first["filter_figure_countries"]),
            sorted(c.id for c in self.countries),
        )
        self.assertEqual(first["filter_figure_events"], [self.event.id])

    def test_save_invalidates(self):
        stale = self.report.get_filter_kwargs
        self.assertEqual(len(stale["filter_figure_countries"]), 2)
        # the serializer edit path: save() first (bumps modified_at), then set M2Ms
        self.report.save()
        self.report.filter_figure_countries.set(self.countries[:1])
        fresh = self.report.get_filter_kwargs
        self.assertEqual(fresh["filter_figure_countries"], [self.countries[0].id])
