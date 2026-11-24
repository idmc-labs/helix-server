import importlib
import json

from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.models import ProtectedError

from apps.organization.models import Organization, OrganizationKind, SourceType
from apps.users.enums import USER_ROLE
from utils.factories import OrganizationFactory, OrganizationKindFactory, SourceTypeFactory
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

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The models as they were at 0012 (the kind still has reliability).
        cls.apps_at_0012 = MigrationLoader(connection).project_state(("organization", "0012_source_type")).apps

    def setUp(self):
        # 0014 dropped the kind's reliability column, which 0012 still writes. Add it back inside this
        # test's transaction (rolled back afterwards, DDL included).
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE organization_organizationkind ADD COLUMN reliability integer NULL")
        clear_taxonomy()

    def _insert(self):
        with connection.schema_editor() as schema_editor:
            taxonomy_migration.insert_source_types(self.apps_at_0012, schema_editor)

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
        legacy = SourceTypeFactory.create(name="Legacy")
        kind = OrganizationKindFactory.create(name="Government", source_type=legacy)
        organization = OrganizationFactory.create(organization_kind=kind)
        self._insert()
        kind.refresh_from_db()
        organization.refresh_from_db()
        self.assertEqual(kind.source_type, legacy)
        self.assertEqual(organization.organization_kind, kind)

    def test_reverse_removes_only_inserted_rows(self):
        other_kind = OrganizationKindFactory.create(name="Media", source_type=SourceTypeFactory.create(name="Legacy"))
        self._insert()
        taxonomy_migration.remove_source_types(self.apps_at_0012, None)
        self.assertEqual(list(SourceType.objects.values_list("name", flat=True)), ["Legacy"])
        self.assertEqual(list(OrganizationKind.objects.values_list("id", flat=True)), [other_kind.id])


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
        self.force_login(create_user_with_role(USER_ROLE.MONITORING_EXPERT.name))

        response = self.query(self.query_str)
        self.assertResponseNoErrors(response)
        data = json.loads(response.content)["data"]
        self.assertEqual(
            data["sourceTypeList"]["results"],
            [
                {"name": "Government", "level": "LEVEL_1", "levelDisplay": "High"},
                {"name": "Media", "level": "LEVEL_3", "levelDisplay": "Low"},
            ],
        )
        self.assertEqual(
            data["organizationKindList"]["results"],
            [
                {"name": "Local Authorities", "sourceType": {"name": "Government", "level": "LEVEL_1"}},
            ],
        )


class TestOrganizationKindMutationsWithSourceType(HelixGraphQLTestCase):
    create_mutation = """
    mutation CreateOrganizationKind($input: OrganizationKindCreateInputType!) {
        createOrganizationKind(data: $input) {
            ok
            errors
            result { id name sourceType { name level } }
        }
    }
    """
    update_mutation = """
    mutation UpdateOrganizationKind($input: OrganizationKindUpdateInputType!) {
        updateOrganizationKind(data: $input) {
            ok
            errors
            result { id name sourceType { name level } }
        }
    }
    """

    def setUp(self):
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))
        self.government = SourceType.objects.create(name="Government", level=SourceType.SOURCE_TYPE_CLASSIFICATION.LEVEL_1)
        self.media = SourceType.objects.create(name="Media", level=SourceType.SOURCE_TYPE_CLASSIFICATION.LEVEL_3)

    def _run(self, mutation, data):
        return json.loads(self.query(mutation, input_data=data).content)

    def test_create_with_source_type(self):
        content = self._run(self.create_mutation, {"name": "Ministries", "sourceType": str(self.government.id)})
        result = content["data"]["createOrganizationKind"]
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["result"]["sourceType"], {"name": "Government", "level": "LEVEL_1"})

    def test_create_without_source_type_is_refused(self):
        content = self._run(self.create_mutation, {"name": "Ministries"})
        self.assertIn("sourceType", content["errors"][0]["message"])
        self.assertFalse(OrganizationKind.objects.filter(name="Ministries").exists())

    def test_create_with_unknown_source_type_is_refused(self):
        content = self._run(self.create_mutation, {"name": "Ministries", "sourceType": "999999"})
        result = content["data"]["createOrganizationKind"]
        self.assertFalse(result["ok"])
        self.assertEqual(result["errors"][0]["field"], "sourceType")

    def test_update_source_type(self):
        kind = OrganizationKindFactory.create(name="Newspapers", source_type=self.government)
        content = self._run(self.update_mutation, {"id": str(kind.id), "sourceType": str(self.media.id)})
        result = content["data"]["updateOrganizationKind"]
        self.assertTrue(result["ok"], result)
        kind.refresh_from_db()
        self.assertEqual(kind.source_type, self.media)

    def test_update_name_only_keeps_source_type(self):
        kind = OrganizationKindFactory.create(name="Newspapers", source_type=self.media)
        content = self._run(self.update_mutation, {"id": str(kind.id), "name": "Press"})
        self.assertTrue(content["data"]["updateOrganizationKind"]["ok"])
        kind.refresh_from_db()
        self.assertEqual((kind.name, kind.source_type), ("Press", self.media))

    def test_update_to_no_source_type_is_refused(self):
        kind = OrganizationKindFactory.create(name="Newspapers", source_type=self.media)
        content = self._run(self.update_mutation, {"id": str(kind.id), "sourceType": None})
        result = content["data"]["updateOrganizationKind"]
        self.assertFalse(result["ok"])
        kind.refresh_from_db()
        self.assertEqual(kind.source_type, self.media)

    def test_kind_type_no_longer_has_reliability(self):
        response = self.query("query { organizationKindList { results { id reliability } } }")
        self.assertIn("reliability", json.loads(response.content)["errors"][0]["message"])
