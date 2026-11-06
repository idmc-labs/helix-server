import importlib
import json

from django.apps import apps as django_apps
from django.db import connection
from django.db.models import ProtectedError

from apps.organization.models import Organization, OrganizationKind, SourceType
from apps.users.enums import USER_ROLE
from utils.factories import OrganizationFactory, OrganizationKindFactory
from utils.tests import HelixGraphQLTestCase, HelixTestCase, create_user_with_role

taxonomy_migration = importlib.import_module("apps.organization.migrations.0012_source_type")


def clear_taxonomy():
    OrganizationKind.objects.all().delete()
    SourceType.objects.all().delete()


EXPECTED_TAXONOMY = {
    ("Government", SourceType.SOURCE_TYPE_CLASSIFICATION.LEVEL_1): {
        "IDP Specific Institutions",
        "National Government",
        "Sub-national Government",
        "Local Authorities",
        "Disaster Agencies",
        "Other",
    },
    ("United Nations", SourceType.SOURCE_TYPE_CLASSIFICATION.LEVEL_1): {"United Nations"},
    ("International Organisations", SourceType.SOURCE_TYPE_CLASSIFICATION.LEVEL_1): {
        "Clusters and Consortia",
        "Intergovernmental Organisations",
        "Red Cross/Red Crescent",
    },
    ("International NGOs", SourceType.SOURCE_TYPE_CLASSIFICATION.LEVEL_2): {"International NGOs"},
    ("Civilians", SourceType.SOURCE_TYPE_CLASSIFICATION.LEVEL_2): {
        "National NGOs and Associations",
        "Academic and Research Institutions",
        "Community Leaders",
        "Affected Population",
        "Other",
    },
    ("Media", SourceType.SOURCE_TYPE_CLASSIFICATION.LEVEL_3): {"Media"},
    ("Other", SourceType.SOURCE_TYPE_CLASSIFICATION.LEVEL_3): {"Private Sector", "Non-State Armed Group", "Unclassified"},
}


class TestSourceTypeTaxonomyMigration(HelixTestCase):
    """the 7 types and 20 subtypes from IDMC's taxonomy."""

    def setUp(self):
        clear_taxonomy()

    def _insert(self):
        with connection.schema_editor() as schema_editor:
            taxonomy_migration.insert_source_types(django_apps, schema_editor)

    def _taxonomy_in_db(self):
        return {
            (source_type.name, source_type.level): set(source_type.organization_kinds.values_list("name", flat=True))
            for source_type in SourceType.objects.all()
        }

    def test_inserts_the_taxonomy(self):
        self._insert()
        self.assertEqual(self._taxonomy_in_db(), EXPECTED_TAXONOMY)
        self.assertEqual(SourceType.objects.count(), 7)
        self.assertEqual(OrganizationKind.objects.filter(source_type__isnull=False).count(), 20)

    def test_is_idempotent(self):
        self._insert()
        self._insert()
        self.assertEqual(SourceType.objects.count(), 7)
        self.assertEqual(OrganizationKind.objects.filter(source_type__isnull=False).count(), 20)

    def test_leaves_existing_kinds_and_organizations_alone(self):
        old_kind = OrganizationKindFactory.create(name="Government")
        organization = OrganizationFactory.create(organization_kind=old_kind)
        self._insert()
        old_kind.refresh_from_db()
        organization.refresh_from_db()
        self.assertIsNone(old_kind.source_type)
        self.assertEqual(organization.organization_kind, old_kind)

    def test_new_kinds_keep_matching_old_reliability(self):
        self._insert()
        reliability = OrganizationKind.ORGANIZATION_RELIABILITY
        expected = {
            SourceType.SOURCE_TYPE_CLASSIFICATION.LEVEL_1: reliability.HIGH,
            SourceType.SOURCE_TYPE_CLASSIFICATION.LEVEL_2: reliability.MEDIUM,
            SourceType.SOURCE_TYPE_CLASSIFICATION.LEVEL_3: reliability.LOW,
        }
        for kind in OrganizationKind.objects.filter(source_type__isnull=False).select_related("source_type"):
            self.assertEqual(kind.reliability, expected[kind.source_type.level], kind.name)

    def test_reverse_removes_only_inserted_rows(self):
        old_kind = OrganizationKindFactory.create(name="Media")
        self._insert()
        taxonomy_migration.remove_source_types(django_apps, None)
        self.assertFalse(SourceType.objects.exists())
        self.assertEqual(list(OrganizationKind.objects.values_list("id", flat=True)), [old_kind.id])


class TestSourceTypeProtection(HelixTestCase):
    def test_source_type_linked_to_a_kind_cannot_be_deleted(self):
        source_type = SourceType.objects.create(name="Media", level=SourceType.SOURCE_TYPE_CLASSIFICATION.LEVEL_3)
        OrganizationKindFactory.create(name="Media", source_type=source_type)
        with self.assertRaises(ProtectedError):
            source_type.delete()

    def test_unused_source_type_can_be_deleted(self):
        source_type = SourceType.objects.create(name="Media", level=SourceType.SOURCE_TYPE_CLASSIFICATION.LEVEL_3)
        source_type.delete()
        self.assertFalse(SourceType.objects.filter(id=source_type.id).exists())

    def test_kind_used_by_an_organization_cannot_be_deleted(self):
        kind = OrganizationKindFactory.create()
        OrganizationFactory.create(organization_kind=kind)
        with self.assertRaises(ProtectedError):
            kind.delete()


class TestDeleteOrganizationKindInUse(HelixGraphQLTestCase):
    """deleting a subtype still used by an organization is refused, naming them."""

    mutation = """
    mutation DeleteOrganizationKind($id: ID!) {
        deleteOrganizationKind(id: $id) {
            ok
            errors
            result { id }
        }
    }
    """

    def setUp(self):
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))
        self.kind = OrganizationKindFactory.create(name="National Government")

    def _delete(self):
        response = self.query(self.mutation, variables={"id": str(self.kind.id)})
        self.assertResponseNoErrors(response)
        return json.loads(response.content)["data"]["deleteOrganizationKind"]

    def test_refused_and_names_the_organizations(self):
        OrganizationFactory.create(name="Ministry B", organization_kind=self.kind)
        OrganizationFactory.create(name="Ministry A", organization_kind=self.kind)
        result = self._delete()
        self.assertFalse(result["ok"])
        message = result["errors"][0]["messages"]
        self.assertIn("National Government is used by 2 organization(s)", message)
        self.assertIn("Ministry A, Ministry B", message)
        self.assertTrue(OrganizationKind.objects.filter(id=self.kind.id).exists())

    def test_archived_organizations_also_block(self):
        organization = OrganizationFactory.create(name="Old Ministry", organization_kind=self.kind)
        organization.delete()  # soft delete (archive)
        self.assertIsNotNone(Organization.objects.get(id=organization.id).deleted_on)
        result = self._delete()
        self.assertFalse(result["ok"])
        self.assertIn("Old Ministry", result["errors"][0]["messages"])

    def test_long_list_is_capped(self):
        for i in range(12):
            OrganizationFactory.create(name=f"Org {i:02d}", organization_kind=self.kind)
        message = self._delete()["errors"][0]["messages"]
        self.assertIn("used by 12 organization(s)", message)
        self.assertIn("Org 09 and 2 more", message)
        self.assertNotIn("Org 10", message)

    def test_unused_kind_is_deleted(self):
        result = self._delete()
        self.assertTrue(result["ok"])
        self.assertFalse(OrganizationKind.objects.filter(id=self.kind.id).exists())


class TestSourceTypeQuery(HelixGraphQLTestCase):
    query_str = """
    query {
        sourceTypeList(ordering: "level,name") {
            results { name level levelDisplay }
        }
        organizationKindList(ordering: "name") {
            results { name sourceType { name level } }
        }
    }
    """

    def test_source_types_and_kind_link(self):
        clear_taxonomy()
        government = SourceType.objects.create(name="Government", level=SourceType.SOURCE_TYPE_CLASSIFICATION.LEVEL_1)
        SourceType.objects.create(name="Media", level=SourceType.SOURCE_TYPE_CLASSIFICATION.LEVEL_3)
        OrganizationKindFactory.create(name="Local Authorities", source_type=government)
        OrganizationKindFactory.create(name="Retired kind")
        self.force_login(create_user_with_role(USER_ROLE.MONITORING_EXPERT.name))

        response = self.query(self.query_str)
        self.assertResponseNoErrors(response)
        data = json.loads(response.content)["data"]
        self.assertEqual(
            data["sourceTypeList"]["results"],
            [
                {"name": "Government", "level": "LEVEL_1", "levelDisplay": "Level 1 (High)"},
                {"name": "Media", "level": "LEVEL_3", "levelDisplay": "Level 3 (Low)"},
            ],
        )
        self.assertEqual(
            data["organizationKindList"]["results"],
            [
                {"name": "Local Authorities", "sourceType": {"name": "Government", "level": "LEVEL_1"}},
                {"name": "Retired kind", "sourceType": None},
            ],
        )
