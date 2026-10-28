"""
Backfill GiddRelease from the published README, CHANGELOG, and StatusLog.

Release metadata is copied as literals from the CHANGELOG block in
apps/gidd/views.py, revision headings in apps/gidd/readme_revisions.py,
the citation in apps/gidd/readme_blocks.py, and run dates in StatusLog.
Later changes to these sources will not affect the backfilled records.

The three pre-2025 generation cycles were never published, so they remain
hidden until an Admin decides to publish them.

Runs are grouped by cycle: one release holds every StatusLog run of its cycle,
retries and failures included. Only runs without a release are attached.
"""

import datetime
import typing

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.gidd.models import GiddRelease, StatusLog


class ReleaseSpec(typing.NamedTuple):
    version: str
    name: str
    release_date: datetime.date
    is_visible_in_gidd: bool
    notes: str
    citation: str = ""
    is_live: bool = False


# Copied from readme_blocks.citation_row().
CITATION_2026 = (
    "All derived work from IDMC data could cite IDMC following this example: Internal Displacement "
    "Monitoring Centre. Global Internal Displacement Database. IDMC (2026). Available at: "
    "https://www.internal-displacement.org/database/displacement-data/ (Accessed: [date of access])."
)
# NOTE: Pre-2025 cycles appear only in StatusLog, not in the published CHANGELOG or README, so
# their run month is used as the version and their run date as the release date.
# Published releases use the CHANGELOG version, date and notes, and the README revision heading.

RELEASES: typing.List[ReleaseSpec] = [
    ReleaseSpec(
        version="2023-05",
        name="May 2023 generation cycle",
        release_date=datetime.date(2023, 5, 11),
        is_visible_in_gidd=False,
        notes="",
    ),
    ReleaseSpec(
        version="2023-11",
        name="November 2023 generation cycle",
        release_date=datetime.date(2023, 11, 15),
        is_visible_in_gidd=False,
        notes="",
    ),
    ReleaseSpec(
        version="2024-05",
        name="May 2024 generation cycle",
        release_date=datetime.date(2024, 5, 13),
        is_visible_in_gidd=False,
        notes="",
    ),
    ReleaseSpec(
        version="2.0",
        name="FIGURES REVIEWED IN JANUARY 2025",
        release_date=datetime.date(
            2025, 1, 31
        ),  # The CHANGELOG gives only "Jan 2025"; the day is the run date in StatusLog.
        is_visible_in_gidd=True,
        notes="Added January 2025 revision round (24 figures).",
    ),
    ReleaseSpec(
        version="3.0",
        name="FIGURES REVIEWED IN MAY 2025",
        release_date=datetime.date(2025, 5, 13),  # CHANGELOG: "May 13, 2025".
        is_visible_in_gidd=True,
        notes="Added May 2025 revision round (61 figures).",
    ),
    ReleaseSpec(
        version="3.1",
        name="FIGURES REVIEWED IN MAY 2026",
        release_date=datetime.date(2026, 5, 12),  # CHANGELOG: "May 12, 2026".
        is_visible_in_gidd=True,
        notes=("Added Q2 2026 revision round (13 figures). Standardized Disasters -> Disaster in revision tables."),
        citation=CITATION_2026,
    ),
    ReleaseSpec(
        version="4",
        name="FIGURES REVIEWED IN SEPTEMBER 2026",
        release_date=datetime.date(2026, 9, 1),  # CHANGELOG: "September 1, 2026".
        is_visible_in_gidd=True,
        notes=(
            "This release includes updates from the Historical data revision project. "
            "All IDP stock figures for 2008–2016 have been updated in the September 2026 "
            "release. Because every IDPs figure was updated, only Internal Displacements "
            "changes are listed in Figures reviewed."
        ),
        citation=CITATION_2026,
        # The latest release: the latest successful run belongs to it, so it is the live one.
        is_live=True,
    ),
]


def release_for_run(triggered_on: datetime.date) -> ReleaseSpec:
    """The release whose cycle a run belongs to.

    A cycle's retries come before the run that published it, so a run belongs to the earliest
    release dated on or after the day it was triggered. A run after the latest release regenerated
    the live data, so it belongs to the latest release.
    """
    for spec in RELEASES:
        if triggered_on <= spec.release_date:
            return spec
    return RELEASES[-1]


class Command(BaseCommand):
    help = "Backfill GIDD releases from the published README and CHANGELOG."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show the planned changes without saving them.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        with transaction.atomic():
            self._backfill(dry_run=dry_run)

            if dry_run:
                transaction.set_rollback(True)

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run: nothing was saved."))

    def _backfill(self, *, dry_run=False):
        releases = {}
        for spec in RELEASES:
            release, created = GiddRelease.objects.get_or_create(
                version=spec.version,
                defaults={
                    "name": spec.name,
                    "release_date": spec.release_date,
                    "notes": spec.notes,
                    "citation": spec.citation or None,
                    "is_visible_in_gidd": spec.is_visible_in_gidd,
                    "is_live": spec.is_live,
                },
            )

            if dry_run:
                action = "Would create" if created else "Already exists"
            else:
                action = "Created" if created else "Exists"

            self.stdout.write(f"{action} release {spec.version} ({spec.name})")
            releases[spec.version] = release

        self._attach_runs(releases)

    def _attach_runs(self, releases):
        # Grouped by `triggered_at`: `completed_at` of some early runs was rewritten months later.
        run_ids = {spec.version: [] for spec in RELEASES}
        for run_id, triggered_at in StatusLog.objects.filter(release__isnull=True).values_list("id", "triggered_at"):
            run_ids[release_for_run(timezone.localdate(triggered_at)).version].append(run_id)
        for version, ids in run_ids.items():
            if ids:
                StatusLog.objects.filter(id__in=ids).update(release=releases[version])
            self.stdout.write(f"Release {version}: attached {len(ids)} run(s)")
