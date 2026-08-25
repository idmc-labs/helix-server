import contextlib
import datetime
from unittest import mock

from django.utils import timezone

from apps.crisis.models import Crisis
from apps.gidd.models import GiddDisplacement, StatusLog
from apps.gidd.tasks import (
    GIDD_GENERATION_LOCK_KEY,
    GIDD_GENERATION_LOCK_TTL,
    GIDD_GENERATION_TIMEOUT,
    kill_all_stale_gidd_generations,
    update_gidd_data,
)
from helix import redis
from utils.factories import CountryFactory, UserFactory
from utils.tests import HelixTestCase

# Listed first because it is the injection point below, not in pipeline order. It writes the
# table whose delete-before-insert property is asserted.
GENERATION_STEPS = [
    "apps.gidd.tasks.update_new_gidd_tables",
    "apps.gidd.tasks.update_public_figure_analysis",
    "apps.gidd.tasks.update_idps_sadd_estimates_country_names",
    "apps.gidd.tasks.update_gidd_event_and_gidd_figure_data",
]


def run_generation(log_id, insert_row=None):
    """Run the task synchronously with the heavy generation steps mocked; the
    delete + insert + status handling under test stay real.

    The step list is iterated rather than patched one index at a time, so adding or removing a
    generation step cannot leave one running for real unnoticed.
    """
    with contextlib.ExitStack() as patches:
        patches.enter_context(mock.patch(GENERATION_STEPS[0], side_effect=insert_row or (lambda: None)))
        for step in GENERATION_STEPS[1:]:
            patches.enter_context(mock.patch(step))
        update_gidd_data(log_id)


class TestGiddGenerationLock(HelixTestCase):
    def setUp(self) -> None:
        self.user = UserFactory.create()

    def make_log(self):
        return StatusLog.objects.create(triggered_by=self.user)

    def test_rerun_replaces_data_instead_of_appending(self):
        # The rebuild must always DELETE before it inserts, so running the
        # generation twice yields ONE data set rather than two appended ones.
        country = CountryFactory.create(name="Nepal", iso3="NPL")

        def insert_row():
            GiddDisplacement.objects.create(
                country=country,
                iso3="NPL",
                country_name="Nepal",
                year=2023,
                cause=Crisis.CRISIS_TYPE.CONFLICT,
                new_displacement=100,
                total_displacement=100,
            )

        for _ in range(2):
            run_generation(self.make_log().id, insert_row)

        self.assertEqual(GiddDisplacement.objects.count(), 1)
        self.assertEqual(StatusLog.objects.filter(status=StatusLog.Status.SUCCESS).count(), 2)

    def test_concurrent_generation_is_refused(self):
        # Hold the redis lock (a concurrent worker would); the task must refuse
        # and mark its run FAILED instead of double-writing.
        log = self.make_log()
        lock = redis.get_lock(GIDD_GENERATION_LOCK_KEY, GIDD_GENERATION_LOCK_TTL)
        assert lock.acquire(blocking=False)
        try:
            run_generation(log.id)
        finally:
            lock.release()

        log.refresh_from_db()
        self.assertEqual(log.status, StatusLog.Status.FAILED)

    def test_pending_run_blocks_until_stale(self):
        log = self.make_log()
        self.assertTrue(StatusLog.has_active_run())

        # A worker killed mid-run leaves PENDING forever; past the staleness
        # window it must stop blocking new triggers.
        StatusLog.objects.filter(id=log.id).update(
            triggered_at=timezone.now() - StatusLog.PENDING_STALE_AFTER - datetime.timedelta(minutes=1)
        )
        self.assertFalse(StatusLog.has_active_run())

    def test_stale_pending_runs_are_marked_failed(self):
        stale = self.make_log()
        StatusLog.objects.filter(id=stale.id).update(
            triggered_at=timezone.now() - StatusLog.PENDING_STALE_AFTER - datetime.timedelta(minutes=1)
        )
        fresh = self.make_log()
        succeeded = self.make_log()
        StatusLog.objects.filter(id=succeeded.id).update(status=StatusLog.Status.SUCCESS)

        kill_all_stale_gidd_generations()

        stale.refresh_from_db()
        fresh.refresh_from_db()
        succeeded.refresh_from_db()
        self.assertEqual(stale.status, StatusLog.Status.FAILED)
        self.assertIsNotNone(stale.completed_at)
        self.assertEqual(fresh.status, StatusLog.Status.PENDING)
        self.assertEqual(succeeded.status, StatusLog.Status.SUCCESS)

    def test_generation_has_a_hard_time_ceiling(self):
        # The soft limit aborts the run (rollback + FAILED via the except path);
        # the stale window must sit above the hard kill backstop so a live run is
        # never flipped by the cleanup.
        self.assertEqual(update_gidd_data.soft_time_limit, GIDD_GENERATION_TIMEOUT)
        self.assertEqual(update_gidd_data.time_limit, GIDD_GENERATION_TIMEOUT + 120)
        # The redis lock's TTL must outlive the hard kill, or an expired lock
        # would let a second run overlap a still-running generation.
        self.assertGreater(GIDD_GENERATION_LOCK_TTL, update_gidd_data.time_limit)
        self.assertGreater(StatusLog.PENDING_STALE_AFTER.total_seconds(), update_gidd_data.time_limit)
