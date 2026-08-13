from datetime import date

from django.core.cache import cache
from django.db import connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.report.dataloaders import ReportLastGenerationLoader, ReportTotalDisaggregationLoader
from apps.report.filters import ReportFilter
from apps.report.models import Report, ReportApproval, ReportGeneration
from apps.users.roles import USER_ROLE
from utils.factories import CountryFactory, EventFactory, FigureFactory, ReportFactory
from utils.tests import HelixTestCase, create_user_with_role


class TestReportTotalDisaggregationLoader(HelixTestCase):
    """The batch's ~18 filter M2M reads are eager-loaded only for the reports whose computed
    filter kwargs are not cached: a cached report's kwargs come from the cache, so its filter
    relations are never read, and loading them would fetch rows nobody looks at.
    """

    # Any query naming this through table is a filter M2M read.
    FILTER_M2M_MARKER = "filter_figure_countries"

    # A report's total_disaggregation must be distinct per report, or a value landing on the
    # wrong key is invisible.
    TOTALS = (11, 22, 33)

    def setUp(self) -> None:
        cache.clear()
        countries = CountryFactory.create_batch(2)
        event = EventFactory.create(event_type=Crisis.CRISIS_TYPE.CONFLICT)
        self.reports = ReportFactory.create_batch(3)
        # Each report filters to its OWN country, and that country holds one figure with a total
        # no other report's does. Without this, no figure exists at all and every report's
        # total_disaggregation is the same all-None dict.
        self.figure_countries = CountryFactory.create_batch(len(self.reports))
        for report, figure_country, total in zip(self.reports, self.figure_countries, self.TOTALS):
            FigureFactory.create(
                country=figure_country,
                event=event,
                category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                role=Figure.ROLE.RECOMMENDED,
                total_figures=total,
                start_date=date(2021, 3, 1),
                end_date=date(2021, 4, 1),
            )
            report.filter_figure_countries.set([*countries, figure_country])
            report.filter_figure_events.set([event])
            report.save()  # .set() does not bump modified_at; save so the cache key is current

    def test_each_report_has_its_own_total(self) -> None:
        # The premise of the positional test below: three reports, three different totals.
        self.assertEqual(
            [report.total_disaggregation["total_flow_conflict_sum"] for report in self.reports],
            list(self.TOTALS),
        )

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
        """Value i belongs to keys[i], whatever order the loader's own queryset returned.

        The key order is deliberately not a palindrome and the missing key does not sit in the
        middle, so reading the map back-to-front produces a different list rather than the same
        one.
        """
        first, second, third = self.reports
        missing = sum(report.id for report in self.reports)  # no such report
        keys = [third.id, missing, first.id, second.id]
        values = ReportTotalDisaggregationLoader().batch_load_fn(keys).get()

        self.assertEqual(
            values,
            [
                third.total_disaggregation,
                None,
                first.total_disaggregation,
                second.total_disaggregation,
            ],
        )
        # Spelled out on the one field that differs per report, so a failure names the report
        # whose total moved rather than diffing four dicts.
        self.assertEqual(
            [value and value["total_flow_conflict_sum"] for value in values],
            [self.TOTALS[2], None, self.TOTALS[0], self.TOTALS[1]],
        )


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


class TestTheLastGenerationBreaksACreatedAtTieByPk(HelixTestCase):
    """Three readers answer "which generation is the report's last one?" and must agree.

    `Report.last_generation`, `ReportLastGenerationLoader` and `ReportFilter`'s review-status
    subquery all order by `-created_at`. `created_at` is not unique -- two generations started in
    the same tick tie -- and a tie under a bare `-created_at` resolves to whatever the plan
    happens to emit first, which differs between the three (a `LIMIT 1` sort, a `DISTINCT ON`, and
    a correlated subquery). Then the list shows one generation and the review-status filter reads
    another. `-id` completes the key so all three name the newest row.

    No fixture ties `created_at` by accident: `auto_now_add` stamps each insert, so the tie is
    forced with `.update()` after the rows exist.
    """

    GENERATION_COUNT = 3

    def setUp(self) -> None:
        self.request = RequestFactory().post("/graphql")
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.request.user = self.admin
        self.report = ReportFactory.create(is_public=True, is_signed_off=False)

        generations = [
            ReportGeneration.objects.create(report=self.report, created_by=self.admin) for _ in range(self.GENERATION_COUNT)
        ]
        # auto_now_add ignores a value passed to the constructor, so the tie is written after.
        tied_at = timezone.now()
        ReportGeneration.objects.filter(report=self.report).update(created_at=tied_at)
        self.generations = list(ReportGeneration.objects.filter(id__in=[g.id for g in generations]).order_by("id"))
        self.newest = self.generations[-1]

        # Every generation EXCEPT the newest is approved, so the review status the filter reports
        # is decided entirely by which generation the tiebreaker picks.
        for generation in self.generations[:-1]:
            ReportApproval.objects.create(generation=generation, created_by=self.admin, is_approved=True)

    def test_the_fixture_really_ties(self) -> None:
        stamps = {generation.created_at for generation in self.generations}
        self.assertEqual(len(stamps), 1, f"the generations must share a created_at: {stamps}")
        self.assertEqual(self.newest.id, max(generation.id for generation in self.generations))

    def test_report_last_generation_takes_the_highest_pk(self) -> None:
        self.assertEqual(self.report.last_generation, self.newest)
        self.assertFalse(self.report.last_generation.is_approved)

    def test_the_loader_takes_the_highest_pk(self) -> None:
        loaded = ReportLastGenerationLoader().batch_load_fn([self.report.id]).get()
        self.assertEqual([generation.id for generation in loaded], [self.newest.id])
        self.assertFalse(loaded[0].is_approved)

    def _filtered(self, review_status) -> list:
        return list(
            ReportFilter(
                data=dict(review_status=[review_status], is_public=True),
                request=self.request,
            ).qs
        )

    def test_the_review_status_filter_reads_the_same_generation(self) -> None:
        # The newest generation is unapproved, so the report is UNAPPROVED and not APPROVED.
        # Reading any older generation flips both answers.
        self.assertNotIn(
            self.report,
            self._filtered(Report.REPORT_REVIEW_FILTER.APPROVED.name),
            "the filter read an older, approved generation",
        )
        self.assertIn(self.report, self._filtered(Report.REPORT_REVIEW_FILTER.UNAPPROVED.name))
