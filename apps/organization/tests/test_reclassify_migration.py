"""A7.2.3: organization migration 0013 moves every organization from its old kind to the mapped subtype,
then removes the old kinds."""

import importlib

from django.apps import apps as django_apps
from django.db import connection

from apps.organization.models import Organization, OrganizationKind
from utils.factories import OrganizationFactory
from utils.tests import HelixTestCase, ensure_source_type_taxonomy

reclassify_migration = importlib.import_module("apps.organization.migrations.0013_reclassify_organizations")
OLD_KIND_TO_SUBTYPE = reclassify_migration.OLD_KIND_TO_SUBTYPE


class TestReclassifyOrganizationsMigration(HelixTestCase):
    def setUp(self):
        # Old kinds have no source type, which 0014 no longer allows. Allow it again inside this test's
        # transaction (rolled back afterwards, DDL included).
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            cursor.execute("ALTER TABLE organization_organizationkind ALTER COLUMN source_type_id DROP NOT NULL")
        ensure_source_type_taxonomy()
        self.old_government = self.old_kind("Government")
        self.old_civil_society = self.old_kind("Civil Society")
        self.ministry = OrganizationFactory.create(name="Ministry", organization_kind=self.old_government)
        self.ngo = OrganizationFactory.create(name="NGO", organization_kind=self.old_civil_society)
        self.archived = OrganizationFactory.create(name="Old Office", organization_kind=self.old_government)
        self.archived.delete()  # soft delete (archive)
        self.no_kind = OrganizationFactory.create(name="Unknown", organization_kind=None)

    def old_kind(self, name):
        return OrganizationKind.objects.create(name=name, source_type=None)

    def migrate(self):
        with connection.schema_editor() as schema_editor:
            reclassify_migration.reclassify_organizations(django_apps, schema_editor)

    def kind_of(self, organization):
        kind = (
            Organization.objects.select_related("organization_kind__source_type").get(id=organization.id).organization_kind
        )
        return (kind.source_type.name, kind.name) if kind else None

    def test_every_mapped_subtype_exists(self):
        subtypes = set(OrganizationKind.objects.filter(source_type__isnull=False).values_list("source_type__name", "name"))
        self.assertEqual(set(OLD_KIND_TO_SUBTYPE.values()) - subtypes, set())

    def test_moves_organizations_and_removes_old_kinds(self):
        self.migrate()
        self.assertEqual(self.kind_of(self.ministry), ("Government", "National Government"))
        self.assertEqual(self.kind_of(self.archived), ("Government", "National Government"))
        self.assertEqual(self.kind_of(self.ngo), ("Civilians", "National NGOs and Associations"))
        self.assertIsNone(self.kind_of(self.no_kind))
        self.assertFalse(OrganizationKind.objects.filter(source_type__isnull=True).exists())
        self.assertEqual(OrganizationKind.objects.count(), 20)

    def test_every_old_kind_is_moved(self):
        for old_kind in OLD_KIND_TO_SUBTYPE:
            OrganizationFactory.create(name=f"Org of {old_kind}", organization_kind=self.old_kind(old_kind))
        self.migrate()
        for old_kind, target in OLD_KIND_TO_SUBTYPE.items():
            self.assertEqual(self.kind_of(Organization.objects.get(name=f"Org of {old_kind}")), target, old_kind)

    def test_running_again_changes_nothing(self):
        self.migrate()
        self.migrate()
        self.assertEqual(self.kind_of(self.ministry), ("Government", "National Government"))
        self.assertEqual(OrganizationKind.objects.count(), 20)

    def test_kind_names_are_matched_loosely(self):
        paper = OrganizationFactory.create(name="Paper", organization_kind=self.old_kind(" MEDIA\xa0"))
        self.migrate()
        self.assertEqual(self.kind_of(paper), ("Media", "Media"))

    def test_unmapped_old_kind_in_use_changes_nothing(self):
        OrganizationFactory.create(organization_kind=self.old_kind("Think Tank"))
        with self.assertRaisesMessage(RuntimeError, "old kind 'Think Tank' is not in OLD_KIND_TO_SUBTYPE"):
            self.migrate()
        self.assertEqual(Organization.objects.get(id=self.ministry.id).organization_kind_id, self.old_government.id)
        self.assertTrue(OrganizationKind.objects.filter(id=self.old_government.id).exists())

    def test_unused_unmapped_old_kind_is_removed(self):
        self.old_kind("Think Tank")
        self.migrate()
        self.assertFalse(OrganizationKind.objects.filter(name="Think Tank").exists())

    def test_missing_subtype_changes_nothing(self):
        OrganizationKind.objects.filter(source_type__name="Government", name="National Government").delete()
        with self.assertRaisesMessage(RuntimeError, "'Government' maps to a subtype that does not exist"):
            self.migrate()
        self.assertEqual(Organization.objects.get(id=self.ministry.id).organization_kind_id, self.old_government.id)
