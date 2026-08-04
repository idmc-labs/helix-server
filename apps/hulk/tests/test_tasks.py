"""
Tests for the hulk bulk-import Celery tasks — specifically the stale-import
backstop that frees the global single-import lock when a worker dies mid-import
and leaves a row stuck at IN_PROGRESS.
"""

from __future__ import annotations

import datetime

from django.test import TestCase
from django.utils import timezone

from apps.hulk.models import HulkBulkImport
from apps.hulk.tasks import HULK_IMPORT_PROGRESS_TIMEOUT, fail_stale_hulk_bulk_imports
from apps.users.enums import USER_ROLE
from utils.tests import create_user_with_role


class TestFailStaleHulkBulkImports(TestCase):
    def setUp(self):
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)

    def _make(self, status, *, started_seconds_ago=None):
        bulk = HulkBulkImport.objects.create(created_by=self.user, status=status)
        if started_seconds_ago is not None:
            bulk.started_at = timezone.now() - datetime.timedelta(seconds=started_seconds_ago)
            bulk.save(update_fields=["started_at"])
        return bulk

    def test_marks_overrun_in_progress_as_failed(self):
        # IN_PROGRESS past the max run time — its worker must be dead.
        stale = self._make(
            HulkBulkImport.HULK_BULK_IMPORT_STATUS.IN_PROGRESS,
            started_seconds_ago=HULK_IMPORT_PROGRESS_TIMEOUT + 60,
        )
        updated = fail_stale_hulk_bulk_imports()
        self.assertEqual(updated, 1)
        stale.refresh_from_db()
        self.assertEqual(stale.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.FAILED)
        self.assertIsNotNone(stale.completed_at)

    def test_leaves_recent_in_progress_untouched(self):
        # A legitimately long-running import still within the limit is spared.
        fresh = self._make(
            HulkBulkImport.HULK_BULK_IMPORT_STATUS.IN_PROGRESS,
            started_seconds_ago=HULK_IMPORT_PROGRESS_TIMEOUT - 60,
        )
        updated = fail_stale_hulk_bulk_imports()
        self.assertEqual(updated, 0)
        fresh.refresh_from_db()
        self.assertEqual(fresh.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.IN_PROGRESS)

    def test_leaves_pending_and_terminal_states_untouched(self):
        # PENDING is handled by process_hulk_bulk_import's stale-skip, not here;
        # terminal states must never be resurrected/re-failed.
        pending = self._make(HulkBulkImport.HULK_BULK_IMPORT_STATUS.PENDING)
        completed = self._make(
            HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED,
            started_seconds_ago=HULK_IMPORT_PROGRESS_TIMEOUT + 60,
        )
        updated = fail_stale_hulk_bulk_imports()
        self.assertEqual(updated, 0)
        pending.refresh_from_db()
        completed.refresh_from_db()
        self.assertEqual(pending.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.PENDING)
        self.assertEqual(completed.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)
