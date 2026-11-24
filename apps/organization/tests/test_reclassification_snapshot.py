import csv
import os
import tempfile
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection

from apps.organization.models import OrganizationKind, SourceType
from utils.factories import EventFactory, FigureFactory, OrganizationFactory
from utils.tests import HelixTestCase, get_subtype


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestReclassificationSnapshot(HelixTestCase):
    """Snapshot taken before and after the reclassification."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.government_other = get_subtype("Government", "Other")
        self.unclassified = get_subtype("Other", "Unclassified")

        self.ministry = OrganizationFactory.create(name="Ministry", organization_kind=self.government_other)
        self.newspaper = OrganizationFactory.create(name="Newspaper", organization_kind=self.unclassified)
        self.figure = FigureFactory.create(event=EventFactory.create())
        self.figure.sources.set([self.ministry, self.newspaper])
        self.no_source_figure = FigureFactory.create(event=self.figure.event)

    def snapshot(self, name):
        # The output directory does not exist yet: the command creates it.
        path = os.path.join(self.tmp, name)
        call_command("snapshot_organization_reclassification", output_dir=path, stdout=StringIO())
        return path

    def test_snapshot_contents(self):
        path = self.snapshot("before")
        organizations = {row["name"]: row for row in read_csv(os.path.join(path, "organizations.csv"))}
        self.assertEqual(organizations["Ministry"]["kind"], "Other")
        self.assertEqual(organizations["Ministry"]["source_type"], "Government")
        self.assertEqual(organizations["Ministry"]["level"], "1")
        self.assertEqual(organizations["Newspaper"]["level"], "3")
        figures = {row["figure_id"]: row for row in read_csv(os.path.join(path, "figures.csv"))}
        # Government (Level 1) and Other (Level 3): the lowest wins.
        self.assertEqual(
            figures[str(self.figure.id)]["classification"], str(SourceType.SOURCE_TYPE_CLASSIFICATION.LEVEL_3.value)
        )
        self.assertEqual(figures[str(self.figure.id)]["idu_source_wording"], "Ministry and Newspaper")
        self.assertEqual(figures[str(self.no_source_figure.id)]["classification"], "")
        self.assertEqual(figures[str(self.no_source_figure.id)]["idu_source_wording"], "")

    def test_before_refused_once_migrated(self):
        # NOTE: the test database is migrated: the kind's reliability column is gone.
        with self.assertRaisesMessage(CommandError, "before snapshot can no longer be taken"):
            call_command("snapshot_organization_reclassification", output_dir=self.tmp, before=True, stdout=StringIO())


class TestReclassificationBeforeSnapshot(HelixTestCase):
    """--before reads the database not yet migrated (organization 0012): old kinds with no source type,
    and the kind's reliability column."""

    def setUp(self):
        # Put the pre-migration schema back inside this test's transaction (rolled back afterwards).
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            cursor.execute("ALTER TABLE organization_organizationkind ALTER COLUMN source_type_id DROP NOT NULL")
            cursor.execute("ALTER TABLE organization_organizationkind ADD COLUMN reliability integer NULL")
        government = self.old_kind("Government", reliability=2)
        local_authority = self.old_kind("Local Authority", reliability=1)
        civil_society = self.old_kind("Civil Society", reliability=0)

        self.ministry = OrganizationFactory.create(name="Ministry", organization_kind=government)
        self.city_hall = OrganizationFactory.create(name="City Hall", organization_kind=local_authority)
        self.ngo = OrganizationFactory.create(name="NGO", organization_kind=civil_society)
        self.no_kind = OrganizationFactory.create(name="Unknown", organization_kind=None)
        event = EventFactory.create()
        self.mixed = FigureFactory.create(event=event)
        self.mixed.sources.set([self.ngo, self.ministry, self.city_hall, self.no_kind])
        self.only_government = FigureFactory.create(event=event)
        self.only_government.sources.set([self.ministry])
        self.no_sources = FigureFactory.create(event=event)

    def old_kind(self, name, reliability):
        kind = OrganizationKind.objects.create(name=name, source_type=None)
        with connection.cursor() as cursor:
            cursor.execute("UPDATE organization_organizationkind SET reliability = %s WHERE id = %s", [reliability, kind.id])
        return kind

    def test_before_snapshot(self):
        # The output directory does not exist yet: the command creates it.
        path = os.path.join(tempfile.mkdtemp(), "before")
        call_command("snapshot_organization_reclassification", output_dir=path, before=True, stdout=StringIO())

        organizations = {row["name"]: row for row in read_csv(os.path.join(path, "organizations.csv"))}
        self.assertEqual(
            {key: organizations["Ministry"][key] for key in ("kind", "source_type", "level", "reliability")},
            {"kind": "Government", "source_type": "", "level": "", "reliability": "High"},
        )
        self.assertEqual(organizations["Unknown"]["reliability"], "")

        figures = {row["figure_id"]: row for row in read_csv(os.path.join(path, "figures.csv"))}
        self.assertEqual(
            figures[str(self.mixed.id)],
            {
                "figure_id": str(self.mixed.id),
                # Low (NGO) to High (Ministry); the source with no kind is left out.
                "reliability": "Low to high",
                # The wording before E7: old kind names collapse to fixed phrases.
                "idu_source_wording": "local authorities, national authorities, NGO, and Unknown",
            },
        )
        self.assertEqual(figures[str(self.only_government.id)]["reliability"], "High")
        self.assertEqual(figures[str(self.only_government.id)]["idu_source_wording"], "national authorities")
        self.assertEqual(figures[str(self.no_sources.id)]["reliability"], "")
        self.assertEqual(figures[str(self.no_sources.id)]["idu_source_wording"], "")

    def test_after_refused_before_migrating(self):
        with self.assertRaisesMessage(CommandError, "have not run yet"):
            call_command("snapshot_organization_reclassification", output_dir=tempfile.mkdtemp(), stdout=StringIO())
