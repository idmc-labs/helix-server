"""A GIDD release locks 7 days after its first successful publish run.

The window starts at the first SUCCESS StatusLog's completed_at: failed runs never start it and a
republish never extends it. It is enforced on release edits, on triggering a run (mutation and
force_update_gidd_data), and again when a queued run actually starts.
"""

import datetime
from io import StringIO
from unittest import mock

from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.gidd.models import StatusLog
from apps.gidd.tests.test_generation_lock import run_generation
from apps.gidd.tests.test_gidd_release_mutations import (
    UPDATE_GIDD_DATA_MUTATION,
    UPDATE_MUTATION,
    make_release,
)
from apps.users.enums import USER_ROLE
from utils.factories import MonitoringSubRegionFactory, UserFactory
from utils.tests import HelixGraphQLTestCase, HelixTestCase, create_user_with_role


def days_ago(days):
    return timezone.now() - datetime.timedelta(days=days)


def make_log(release, user, status, completed_days_ago=None):
    return StatusLog.objects.create(
        triggered_by=user,
        release=release,
        status=status,
        completed_at=days_ago(completed_days_ago) if completed_days_ago is not None else None,
    )


class TestReleaseEditWindow(HelixTestCase):
    def setUp(self) -> None:
        self.user = UserFactory.create()
        self.release = make_release()

    def test_draft_is_open(self):
        self.assertIsNone(self.release.first_published_at())
        self.assertFalse(self.release.is_edit_window_closed())

    def test_failed_runs_do_not_start_the_window(self):
        make_log(self.release, self.user, StatusLog.Status.FAILED, completed_days_ago=30)
        self.assertIsNone(self.release.first_published_at())
        self.assertFalse(self.release.is_edit_window_closed())

    def test_open_within_seven_days(self):
        make_log(self.release, self.user, StatusLog.Status.SUCCESS, completed_days_ago=6)
        self.assertFalse(self.release.is_edit_window_closed())

    def test_closed_after_seven_days(self):
        make_log(self.release, self.user, StatusLog.Status.SUCCESS, completed_days_ago=8)
        self.assertTrue(self.release.is_edit_window_closed())

    def test_republish_does_not_extend_the_window(self):
        make_log(self.release, self.user, StatusLog.Status.SUCCESS, completed_days_ago=8)
        make_log(self.release, self.user, StatusLog.Status.SUCCESS, completed_days_ago=1)
        self.assertTrue(self.release.is_edit_window_closed())

    def test_other_releases_runs_do_not_count(self):
        make_log(make_release(version="2"), self.user, StatusLog.Status.SUCCESS, completed_days_ago=30)
        self.assertFalse(self.release.is_edit_window_closed())


class TestReleaseUpdateMutationWindow(HelixGraphQLTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.admin = create_user_with_role(
            USER_ROLE.ADMIN.name,
            monitoring_sub_region=MonitoringSubRegionFactory.create().id,
        )
        self.release = make_release(citation="Old citation")
        self.force_login(self.admin)

    def _update(self, **data):
        return self.query(UPDATE_MUTATION, variables={"data": {"id": self.release.id, **data}})

    def test_published_release_editable_within_window(self):
        make_log(self.release, self.admin, StatusLog.Status.SUCCESS, completed_days_ago=3)
        content = self._update(notes="Fixed typo.").json()["data"]["updateGiddRelease"]
        self.assertTrue(content["ok"], content)

    def test_published_release_refused_after_window(self):
        make_log(self.release, self.admin, StatusLog.Status.SUCCESS, completed_days_ago=8)
        for field, value in [
            ("citation", "New citation"),
            ("notes", "New notes"),
        ]:
            with self.subTest(field=field):
                content = self._update(**{field: value}).json()["data"]["updateGiddRelease"]
                self.assertFalse(content["ok"], content)
        self.release.refresh_from_db()
        self.assertEqual(self.release.citation, "Old citation")
        self.assertEqual(self.release.notes, "Notes.")


class TestGiddUpdateDataWindow(HelixGraphQLTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.admin = create_user_with_role(
            USER_ROLE.ADMIN.name,
            monitoring_sub_region=MonitoringSubRegionFactory.create().id,
        )
        self.release = make_release()
        self.force_login(self.admin)

    def _trigger(self, release_id):
        # GraphQL test case does not run on_commit hooks by itself.
        with mock.patch("apps.gidd.tasks.update_gidd_data") as task, self.captureOnCommitCallbacks(execute=True):
            response = self.query(UPDATE_GIDD_DATA_MUTATION, variables={"releaseId": release_id})
        return response.json()["data"]["giddUpdateData"], task

    def test_republish_allowed_within_window(self):
        make_log(self.release, self.admin, StatusLog.Status.SUCCESS, completed_days_ago=3)
        content, task = self._trigger(self.release.id)
        self.assertTrue(content["ok"], content)
        task.delay.assert_called_once()

    def test_refused_after_window(self):
        make_log(self.release, self.admin, StatusLog.Status.SUCCESS, completed_days_ago=8)
        content, task = self._trigger(self.release.id)
        self.assertFalse(content["ok"])
        self.assertIn("new release", str(content["errors"]))
        self.assertEqual(StatusLog.objects.count(), 1)
        task.delay.assert_not_called()

    def test_missing_release_refused(self):
        for release_id in [self.release.id + 1000, "abc"]:
            with self.subTest(release_id=release_id):
                content, task = self._trigger(release_id)
                self.assertFalse(content["ok"])
                task.delay.assert_not_called()
        self.assertFalse(StatusLog.objects.exists())


class TestQueuedRunRecheck(HelixTestCase):
    def setUp(self) -> None:
        self.user = UserFactory.create()
        self.release = make_release()

    def test_queued_run_refused_once_window_closed(self):
        # Triggered inside the window, but the worker picks it up after it closed.
        make_log(self.release, self.user, StatusLog.Status.SUCCESS, completed_days_ago=8)
        log = make_log(self.release, self.user, StatusLog.Status.PENDING)
        run_generation(log.id)
        log.refresh_from_db()
        self.assertEqual(log.status, StatusLog.Status.FAILED)
        self.release.refresh_from_db()
        self.assertFalse(self.release.is_live)

    def test_run_within_window_publishes(self):
        make_log(self.release, self.user, StatusLog.Status.SUCCESS, completed_days_ago=3)
        log = make_log(self.release, self.user, StatusLog.Status.PENDING)
        run_generation(log.id)
        log.refresh_from_db()
        self.assertEqual(log.status, StatusLog.Status.SUCCESS)


class TestForceUpdateGiddDataCommand(HelixTestCase):
    def setUp(self) -> None:
        self.user = UserFactory.create()
        self.release = make_release()

    def _call(self, release_id=None):
        args = [] if release_id is None else ["--release-id", str(release_id)]
        call_command("force_update_gidd_data", *args, stdout=StringIO())

    def test_release_argument_is_required(self):
        with self.assertRaises(CommandError):
            self._call()
        self.assertFalse(StatusLog.objects.exists())

    def test_missing_release_refused(self):
        with self.assertRaises(CommandError):
            self._call(self.release.id + 1000)
        self.assertFalse(StatusLog.objects.exists())

    def test_refused_after_window(self):
        make_log(self.release, self.user, StatusLog.Status.SUCCESS, completed_days_ago=8)
        with mock.patch("apps.gidd.tasks.update_gidd_data") as task:
            with self.assertRaises(CommandError):
                self._call(self.release.id)
        task.assert_not_called()
        self.assertEqual(StatusLog.objects.count(), 1)

    def test_refused_while_run_in_progress(self):
        make_log(self.release, self.user, StatusLog.Status.PENDING)
        with mock.patch("apps.gidd.tasks.update_gidd_data") as task:
            with self.assertRaises(CommandError):
                self._call(self.release.id)
        task.assert_not_called()

    def test_runs_synchronously_against_the_release(self):
        with mock.patch("apps.gidd.tasks.update_gidd_data") as task:
            self._call(self.release.id)
        log = StatusLog.objects.get()
        self.assertEqual(log.release, self.release)
        task.assert_called_once_with(log_id=log.id)
        task.delay.assert_not_called()


class TestVisibilitySetByFirstPublish(HelixTestCase):
    def setUp(self) -> None:
        self.user = UserFactory.create()
        self.release = make_release()

    def _run(self, fail=False):
        log = make_log(self.release, self.user, StatusLog.Status.PENDING)

        def maybe_fail():
            if fail:
                raise RuntimeError("generation failed")

        run_generation(log.id, insert_row=maybe_fail)
        self.release.refresh_from_db()

    def test_draft_is_hidden(self):
        self.assertFalse(self.release.is_visible_in_gidd)

    def test_first_successful_run_makes_it_visible(self):
        self._run()
        self.assertTrue(self.release.is_visible_in_gidd)

    def test_failed_run_keeps_it_hidden(self):
        self._run(fail=True)
        self.assertFalse(self.release.is_visible_in_gidd)

    def test_republish_keeps_a_hidden_published_release_hidden(self):
        self._run()
        self.release.is_visible_in_gidd = False
        self.release.save(update_fields=["is_visible_in_gidd"])
        self._run()
        self.assertFalse(self.release.is_visible_in_gidd)
