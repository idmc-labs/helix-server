from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.report.dataloaders import ReportTotalDisaggregationLoader
from apps.report.models import Report
from utils.factories import CountryFactory, EventFactory, ReportFactory
from utils.tests import HelixTestCase


class TestReportTotalDisaggregationLoader(HelixTestCase):
    """The batch's ~18 filter M2M reads are eager-loaded only for the reports whose computed
    filter kwargs are not cached: a cached report's kwargs come from the cache, so its filter
    relations are never read, and loading them would fetch rows nobody looks at.
    """

    # Any query naming this through table is a filter M2M read.
    FILTER_M2M_MARKER = "filter_figure_countries"

    def setUp(self) -> None:
        cache.clear()
        countries = CountryFactory.create_batch(2)
        event = EventFactory.create()
        self.reports = ReportFactory.create_batch(3)
        for report in self.reports:
            report.filter_figure_countries.set(countries)
            report.filter_figure_events.set([event])
            report.save()  # .set() does not bump modified_at; save so the cache key is current

    def _load(self, reports):
        keys = [report.id for report in reports]
        with CaptureQueriesContext(connection) as ctx:
            values = ReportTotalDisaggregationLoader().batch_load_fn(keys).get()
        return values, ctx.captured_queries

    def _filter_m2m_queries(self, captured):
        return [query["sql"] for query in captured if self.FILTER_M2M_MARKER in query["sql"]]

    def test_cold_cache_reads_the_filter_relations_once_for_the_batch(self) -> None:
        one_report, _ = self._load(self.reports[:1])
        cache.clear()
        three_reports, captured = self._load(self.reports)

        self.assertTrue(self._filter_m2m_queries(captured), "a cold batch must read the filter relations")
        self.assertEqual(three_reports[0], one_report[0])

        # One eager load for the whole batch: growing the batch adds its aggregates, not
        # another ~18 relation reads.
        cache.clear()
        _, captured_one = self._load(self.reports[:1])
        cache.clear()
        _, captured_three = self._load(self.reports)
        self.assertEqual(len(captured_three) - len(captured_one), 2, [q["sql"] for q in captured_three])

    def test_warm_cache_reads_no_filter_relation(self) -> None:
        cold_values, cold_queries = self._load(self.reports)
        warm_values, warm_queries = self._load(self.reports)

        self.assertEqual(warm_values, cold_values)
        self.assertEqual(self._filter_m2m_queries(warm_queries), [])
        # What is left: the report rows plus one aggregate per report.
        self.assertEqual(len(warm_queries), 1 + len(self.reports), [q["sql"] for q in warm_queries])
        self.assertLess(len(warm_queries), len(cold_queries))

    def test_only_the_reports_missing_from_the_cache_are_eager_loaded(self) -> None:
        self._load(self.reports)  # warm all three
        stale, fresh = self.reports[0], self.reports[1]
        stale.save()  # bumps modified_at, so this report's key rotates

        values, captured = self._load(self.reports)
        relation_reads = self._filter_m2m_queries(captured)
        self.assertTrue(relation_reads, "the report missing from the cache must still be read")
        for sql in relation_reads:
            self.assertIn(str(stale.id), sql, sql)
            self.assertNotIn(str(fresh.id), sql, sql)

        # And the values are the same ones the fully cached batch reported.
        self.assertEqual(values, self._load(self.reports)[0])

    def test_values_follow_key_order(self) -> None:
        first, second = self.reports[0], self.reports[1]
        missing = sum(report.id for report in self.reports)  # no such report
        keys = [second.id, missing, first.id]
        values = ReportTotalDisaggregationLoader().batch_load_fn(keys).get()

        self.assertEqual(values[1], None)
        self.assertEqual(values[0], second.total_disaggregation)
        self.assertEqual(values[2], first.total_disaggregation)


class TestUncachedFilterKwargsSelection(HelixTestCase):
    """`with_uncached_filter_kwargs` reports exactly the instances a caller still has to
    read the filter relations for."""

    def setUp(self) -> None:
        cache.clear()
        self.reports = ReportFactory.create_batch(3)

    def test_all_uncached_before_any_read(self) -> None:
        self.assertEqual(
            Report.with_uncached_filter_kwargs(self.reports),
            self.reports,
        )

    def test_a_read_instance_drops_out_and_a_save_brings_it_back(self) -> None:
        cached, other = self.reports[0], self.reports[1]
        cached.get_filter_kwargs
        self.assertNotIn(cached, Report.with_uncached_filter_kwargs(self.reports))
        self.assertIn(other, Report.with_uncached_filter_kwargs(self.reports))

        cached.save()
        self.assertIn(cached, Report.with_uncached_filter_kwargs(self.reports))

    def test_an_unsaved_instance_is_uncached(self) -> None:
        unsaved = Report()
        self.assertEqual(Report.with_uncached_filter_kwargs([unsaved]), [unsaved])
