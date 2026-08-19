from contextlib import contextmanager
from unittest import mock

from django.test import SimpleTestCase

from apps.contrib import tasks
from helix import redis as helix_redis

# One lock per api type. A shared key would starve two of the three every cycle,
# since all of them fire in the same `0 */2` slot.
LOCK_KEYS = {
    "generate_idus_dump_file": "generate_idus_dump_file",
    "generate_idus_all_dump_file": "generate_idus_all_dump_file",
    "generate_idus_all_disaster_dump_file": "generate_idus_all_disaster_dump_file",
}


class TestIdusDumpLocking(SimpleTestCase):
    """A dump run that is already in flight must not be joined by a second one.

    Both rewrite the same `ExternalApiDump` rows and S3 objects for their api type.
    """

    def setUp(self):
        self._clear_locks()
        self.addCleanup(self._clear_locks)
        patcher = mock.patch.object(tasks, "_generate_idus_dump_file", return_value="generated")
        self.generate = patcher.start()
        self.addCleanup(patcher.stop)

    def _clear_locks(self):
        helix_redis.get_connection().delete(*LOCK_KEYS.values())

    @contextmanager
    def _held(self, key):
        lock = helix_redis.get_lock(key, tasks.IDUS_DUMP_LOCK_TIMEOUT)
        self.assertTrue(lock.acquire(blocking=False))
        try:
            yield
        finally:
            lock.release()

    def test_an_unlocked_task_runs_and_frees_its_lock(self):
        for task_name in LOCK_KEYS:
            with self.subTest(task=task_name):
                self.assertEqual(getattr(tasks, task_name)(), "generated")
                self.assertEqual(getattr(tasks, task_name)(), "generated")

    def test_a_held_lock_skips_only_its_own_task(self):
        for task_name, key in LOCK_KEYS.items():
            with self.subTest(task=task_name):
                self.generate.reset_mock()
                with self._held(key):
                    self.assertIs(getattr(tasks, task_name)(), False)
                    self.generate.assert_not_called()

                    for sibling in LOCK_KEYS.keys() - {task_name}:
                        self.assertEqual(getattr(tasks, sibling)(), "generated")
