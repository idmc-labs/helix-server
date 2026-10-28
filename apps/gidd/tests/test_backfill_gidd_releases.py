import datetime
from io import StringIO

from django.core.management import call_command
from django.utils import timezone

from apps.gidd.models import GiddRelease, StatusLog
from utils.factories import UserFactory
from utils.tests import HelixTestCase


def _at(year, month, day):
    return timezone.make_aware(datetime.datetime(year, month, day, 12))


class TestBackfillGiddReleases(HelixTestCase):
    def _run(self, triggered_at, status=StatusLog.Status.SUCCESS, release=None):
        log = StatusLog.objects.create(triggered_by=UserFactory.create(), status=status, release=release)
        # `triggered_at` is auto_now_add, so the date has to be written after the insert.
        StatusLog.objects.filter(id=log.id).update(triggered_at=triggered_at)
        return log

    def _version_of(self, run):
        run.refresh_from_db()
        return run.release.version

    def _backfill(self, *args):
        call_command("backfill_gidd_releases", *args, stdout=StringIO())

    def test_creates_one_release_per_cycle(self):
        self._backfill()
        self.assertEqual(
            list(GiddRelease.objects.order_by("release_date").values_list("version", flat=True)),
            ["2023-05", "2023-11", "2024-05", "2.0", "3.0", "3.1", "4"],
        )

    def test_unannounced_cycles_are_hidden_from_the_readme(self):
        self._backfill()
        hidden = set(GiddRelease.objects.filter(is_visible_in_gidd=False).values_list("version", flat=True))
        self.assertEqual(hidden, {"2023-05", "2023-11", "2024-05"})

    def test_notes_come_from_the_published_changelog(self):
        self._backfill()
        self.assertEqual(GiddRelease.objects.get(version="3.0").notes, "Added May 2025 revision round (61 figures).")
        self.assertEqual(GiddRelease.objects.get(version="2023-05").notes, "")

    def test_names_come_from_the_revision_headings(self):
        self._backfill()
        self.assertEqual(GiddRelease.objects.get(version="4").name, "FIGURES REVIEWED IN SEPTEMBER 2026")
        self.assertEqual(GiddRelease.objects.get(version="2.0").name, "FIGURES REVIEWED IN JANUARY 2025")

    def test_release_dates_are_changelog_dates(self):
        self._backfill()
        self.assertEqual(GiddRelease.objects.get(version="4").release_date, datetime.date(2026, 9, 1))
        self.assertEqual(GiddRelease.objects.get(version="3.0").release_date, datetime.date(2025, 5, 13))

    def test_citation_is_set_only_on_2026_releases(self):
        self._backfill()
        with_citation = set(GiddRelease.objects.filter(citation__isnull=False).values_list("version", flat=True))
        self.assertEqual(with_citation, {"3.1", "4"})
        self.assertIn("IDMC (2026)", GiddRelease.objects.get(version="4").citation)

    def test_runs_are_grouped_by_cycle_retries_and_failures_included(self):
        cycle = [
            self._run(_at(2024, 5, 13), StatusLog.Status.FAILED),
            self._run(_at(2024, 5, 13), StatusLog.Status.FAILED),
            self._run(_at(2024, 5, 13)),
        ]
        latest = [self._run(_at(2026, 8, 28)), self._run(_at(2026, 8, 31))]
        self._backfill()
        self.assertEqual({self._version_of(run) for run in cycle}, {"2024-05"})
        self.assertEqual({self._version_of(run) for run in latest}, {"4"})

    def test_run_belongs_to_the_earliest_release_on_or_after_it(self):
        before_first = self._run(_at(2023, 5, 10))
        between = self._run(_at(2025, 3, 1))
        after_last = self._run(_at(2026, 9, 15))
        self._backfill()
        self.assertEqual(self._version_of(before_first), "2023-05")
        self.assertEqual(self._version_of(between), "3.0")
        self.assertEqual(self._version_of(after_last), "4")

    def test_attached_runs_are_not_moved(self):
        self._backfill()
        release = GiddRelease.objects.get(version="2.0")
        run = self._run(_at(2026, 8, 31), release=release)
        self._backfill()
        run.refresh_from_db()
        self.assertEqual(run.release, release)

    def test_latest_release_is_live(self):
        self._backfill()
        self.assertEqual(list(GiddRelease.objects.filter(is_live=True).values_list("version", flat=True)), ["4"])

    def test_rerunning_is_a_no_op(self):
        self._backfill()
        GiddRelease.objects.filter(version="4").update(notes="Edited by an Admin.")
        self._backfill()
        self.assertEqual(GiddRelease.objects.count(), 7)
        self.assertEqual(GiddRelease.objects.filter(is_live=True).count(), 1)
        self.assertEqual(GiddRelease.objects.get(version="4").notes, "Edited by an Admin.")

    def test_dry_run_saves_nothing(self):
        self._backfill("--dry-run")
        self.assertFalse(GiddRelease.objects.exists())
