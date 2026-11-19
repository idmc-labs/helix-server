import csv
import os
import tempfile
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError

from apps.organization.models import OrganizationKind, SourceType
from utils.factories import EventFactory, FigureFactory, OrganizationFactory, OrganizationKindFactory
from utils.tests import HelixTestCase, ensure_source_type_taxonomy

RELIABILITY = OrganizationKind.ORGANIZATION_RELIABILITY


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestSourceClassificationSnapshot(HelixTestCase):
    """Snapshot before and after the reclassification, then summarize the changes."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Old kinds (no source type), as before A7.2.3.
        self.old_government = OrganizationKindFactory.create(name="Government", reliability=RELIABILITY.HIGH)
        self.old_media = OrganizationKindFactory.create(name="Media", reliability=RELIABILITY.LOW)
        # New subtypes from migration 0012.
        ensure_source_type_taxonomy()
        self.national_government = OrganizationKind.objects.get(name="National Government")
        self.media = OrganizationKind.objects.get(name="Media", source_type__name="Media")

        self.ministry = OrganizationFactory.create(name="Ministry", organization_kind=self.old_government)
        self.newspaper = OrganizationFactory.create(name="Newspaper", organization_kind=self.old_media)
        self.figure = FigureFactory.create(event=EventFactory.create())
        self.figure.sources.set([self.ministry, self.newspaper])
        self.no_source_figure = FigureFactory.create(event=self.figure.event)

    def snapshot(self, name):
        path = os.path.join(self.tmp, name)
        call_command("snapshot_source_classification", path, stdout=StringIO())
        return path

    def compare(self, before, after):
        out_dir = os.path.join(self.tmp, "compare")
        call_command("compare_source_classification", before, after, out_dir, stdout=StringIO())
        return out_dir

    def test_snapshot_contents(self):
        path = self.snapshot("before")
        organizations = {row["name"]: row for row in read_csv(os.path.join(path, "organizations.csv"))}
        self.assertEqual(organizations["Ministry"]["kind"], "Government")
        self.assertEqual(organizations["Ministry"]["source_type"], "")
        figures = {row["figure_id"]: row for row in read_csv(os.path.join(path, "figures.csv"))}
        # Government -> Level 1 and Media -> Level 3 by the old-reliability fallback; lowest wins.
        self.assertEqual(
            figures[str(self.figure.id)]["classification"], str(SourceType.SOURCE_TYPE_CLASSIFICATION.LEVEL_3.value)
        )
        self.assertEqual(figures[str(self.figure.id)]["idu_source_wording"], "national authorities and media sources")
        self.assertEqual(figures[str(self.no_source_figure.id)]["classification"], "")
        self.assertEqual(figures[str(self.no_source_figure.id)]["idu_source_wording"], "")

    def test_compare_summarizes_moves_and_changes(self):
        before = self.snapshot("before")
        self.ministry.organization_kind = self.national_government
        self.ministry.save()
        self.newspaper.organization_kind = self.media
        self.newspaper.save()
        after = self.snapshot("after")

        out_dir = self.compare(before, after)
        moved = {row["name"]: row for row in read_csv(os.path.join(out_dir, "organizations_moved.csv"))}
        self.assertEqual(moved["Ministry"]["kind_before"], "Government")
        self.assertEqual(moved["Ministry"]["kind_after"], "Government - National Government")
        self.assertEqual(moved["Newspaper"]["kind_after"], "Media - Media")

        changed = {row["figure_id"]: row for row in read_csv(os.path.join(out_dir, "figures_changed.csv"))}
        # Level unchanged (3); the wording changes until A7.2.4 maps the new subtype names.
        self.assertEqual(changed[str(self.figure.id)]["level_before"], changed[str(self.figure.id)]["level_after"])
        self.assertNotEqual(
            changed[str(self.figure.id)]["idu_source_wording_before"],
            changed[str(self.figure.id)]["idu_source_wording_after"],
        )
        with open(os.path.join(out_dir, "report.md"), encoding="utf-8") as f:
            report = f.read()
        self.assertIn("| Government | Government - National Government | 1 |", report)
        self.assertNotIn("## Problems", report)

    def test_nothing_changed(self):
        before = self.snapshot("before")
        after = self.snapshot("after")
        out_dir = self.compare(before, after)
        self.assertEqual(read_csv(os.path.join(out_dir, "organizations_moved.csv")), [])
        self.assertEqual(read_csv(os.path.join(out_dir, "figures_changed.csv")), [])

    def test_organization_losing_its_kind_fails(self):
        before = self.snapshot("before")
        self.ministry.organization_kind = None
        self.ministry.save()
        after = self.snapshot("after")
        with self.assertRaises(CommandError):
            self.compare(before, after)
