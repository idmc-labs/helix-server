from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import RequestFactory, SimpleTestCase, TestCase, TransactionTestCase
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from helix.celery import app as celery_app
from helix.celery_beat import HelixDatabaseScheduler

# celery installs this entry itself; it is owned by beat, not by beat_schedule.
CELERY_DEFAULT_ENTRY = "celery.backend_cleanup"


class TestHelixDatabaseScheduler(TransactionTestCase):
    """`beat_schedule` owns every field of a `PeriodicTask` except `enabled`.

    A task an admin switched off has to stay off across the next beat restart,
    while a schedule edited in code still reaches the database. The scheduler
    calls `close_old_connections()`, so these cases need real transactions
    rather than `TestCase`'s wrapping atomic block.
    """

    def _start_beat(self):
        scheduler = HelixDatabaseScheduler(app=celery_app, lazy=False)
        # Beat's exit-time sync() would otherwise write after teardown.
        self.addCleanup(scheduler._finalize.cancel)
        return scheduler

    def test_startup_seeds_beat_schedule(self):
        self._start_beat()
        names = set(PeriodicTask.objects.values_list("name", flat=True))
        self.assertTrue(set(celery_app.conf.beat_schedule).issubset(names))
        self.assertLessEqual(names - set(celery_app.conf.beat_schedule), {CELERY_DEFAULT_ENTRY})

    def test_startup_keeps_enabled_but_rewrites_the_schedule(self):
        self._start_beat()
        task = PeriodicTask.objects.get(name="kill-exports")
        PeriodicTask.objects.filter(pk=task.pk).update(enabled=False)
        CrontabSchedule.objects.filter(pk=task.crontab_id).update(minute="42")

        self._start_beat()

        task.refresh_from_db()
        self.assertFalse(task.enabled)
        self.assertEqual(task.crontab.minute, "*/15")

    def test_startup_drops_entries_no_longer_in_code(self):
        self._start_beat()
        PeriodicTask.objects.create(
            name="removed-from-code",
            task="apps.contrib.tasks.kill_all_old_excel_exports",
            crontab=CrontabSchedule.objects.first(),
        )

        self._start_beat()

        self.assertFalse(PeriodicTask.objects.filter(name="removed-from-code").exists())

    def test_expiry_reaches_the_published_message(self):
        scheduler = self._start_beat()
        for name, entry in celery_app.conf.beat_schedule.items():
            with self.subTest(entry=name):
                ttl = entry["options"]["expire_seconds"]
                # `expire_seconds` is the only spelling DatabaseScheduler persists;
                # it re-emerges as the `expires` kwarg beat hands to apply_async.
                self.assertEqual(PeriodicTask.objects.get(name=name).expire_seconds, ttl)
                self.assertEqual(scheduler.schedule[name].options["expires"], ttl)

    def test_disabled_task_leaves_the_live_schedule(self):
        self.assertIn("kill-exports", self._start_beat().schedule)
        PeriodicTask.objects.filter(name="kill-exports").update(enabled=False)
        self.assertNotIn("kill-exports", self._start_beat().schedule)


def _period_seconds(schedule):
    """Seconds between two consecutive fires of `schedule`, read off the crontab."""
    minute, hour = schedule._orig_minute, schedule._orig_hour
    if minute.startswith("*/") and hour == "*":
        return int(minute[2:]) * 60
    if hour.startswith("*/") and minute.isdigit():
        return int(hour[2:]) * 60 * 60
    raise AssertionError(f"no period rule for {schedule}")


class TestBeatScheduleExpiry(SimpleTestCase):
    """A queued run must not outlive its own period.

    Without this cap a worker outage lets beat stack one message per tick, and
    the whole backlog runs back to back once workers return.
    """

    def test_every_entry_expires_after_one_period(self):
        for name, entry in celery_app.conf.beat_schedule.items():
            with self.subTest(entry=name):
                self.assertEqual(
                    entry["options"]["expire_seconds"],
                    _period_seconds(entry["schedule"]),
                )


class TestPeriodicTaskAdmin(SimpleTestCase):
    def test_only_enabled_is_editable(self):
        model_admin = admin.site._registry[PeriodicTask]
        shown = {field for _, options in model_admin.fieldsets for field in options["fields"]}
        self.assertEqual(shown - set(model_admin.readonly_fields), {"enabled"})
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_delete_permission(None))

    def test_schedule_models_are_not_registered(self):
        self.assertNotIn(CrontabSchedule, admin.site._registry)


class TestPeriodicTaskAdminPermissions(TestCase):
    """Every action on this admin writes to a task or fires it."""

    def _staff_user_with(self, codename):
        user = get_user_model().objects.create_user(
            username=f"{codename}@example.com",
            email=f"{codename}@example.com",
            password="password",
            is_staff=True,
        )
        user.user_permissions.add(Permission.objects.get(codename=codename))
        return get_user_model().objects.get(pk=user.pk)

    def _request(self, user):
        request = RequestFactory().get("/admin/django_celery_beat/periodictask/")
        request.user = user
        return request

    def test_view_only_staff_gets_no_actions(self):
        model_admin = admin.site._registry[PeriodicTask]
        request = self._request(self._staff_user_with("view_periodictask"))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertEqual(model_admin.get_actions(request), {})

    def test_staff_with_change_permission_gets_the_actions(self):
        model_admin = admin.site._registry[PeriodicTask]
        request = self._request(self._staff_user_with("change_periodictask"))
        self.assertEqual(
            set(model_admin.get_actions(request)),
            {"enable_tasks", "disable_tasks", "run_tasks"},
        )
