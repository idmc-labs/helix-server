import json

from apps.organization.models import Organization
from apps.users.enums import USER_ROLE
from utils.factories import (
    ContactFactory,
    CountryFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
    OrganizationFactory,
)
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestSoftDeletedOrganizationVisibility(HelixGraphQLTestCase):
    """Pins that an archived Organization stays visible everywhere until a caller hides it.

    `deleted_on` marks an archived row, not a removed one. Nothing hides it on its own
    initiative: not the manager, and not the filterset. A filtering default manager -- or a
    filterset that hides by default -- also removes the row from entry.publishers and
    figure.sources, so archiving an organization stripped attribution from live records that
    were never archived. The lists that offer organizations for selection pass
    `excludeDeleted: true`; every other read reports the real association.
    """

    def setUp(self) -> None:
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(self.user)

    def test_list_shows_an_archived_organization_by_default(self):
        visible = OrganizationFactory.create(name="visible-org")
        removed = OrganizationFactory.create(name="removed-org")
        removed.delete()

        response = self.query(
            """
            query MyQuery { organizationList { totalCount results { id name } } }
            """,
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        ids = [o["id"] for o in content["data"]["organizationList"]["results"]]
        self.assertIn(str(visible.id), ids, content)
        self.assertIn(str(removed.id), ids, content)

    def test_list_hides_an_archived_organization_when_asked(self):
        """`excludeDeleted: true` is what a selection input sends."""
        visible = OrganizationFactory.create(name="visible-org")
        removed = OrganizationFactory.create(name="removed-org")
        removed.delete()

        response = self.query(
            """
            query MyQuery($filters: OrganizationFilterDataInputType) {
              organizationList(filters: $filters) { totalCount results { id name } }
            }
            """,
            variables={"filters": {"excludeDeleted": True}},
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        ids = [o["id"] for o in content["data"]["organizationList"]["results"]]
        self.assertIn(str(visible.id), ids, content)
        self.assertNotIn(str(removed.id), ids, content)
        self.assertEqual(content["data"]["organizationList"]["totalCount"], len(ids), content)

    def test_explicit_null_excludes_nothing(self):
        """An explicit `null` must read as "the caller said nothing", not as a hide.

        Stored export filter dicts carry every key, so the value arrives explicitly. The
        filter method is never called for an empty value, which is what keeps the two
        equivalent -- reading `self.data` directly would take the hide branch here.
        """
        removed = OrganizationFactory.create(name="removed-org")
        removed.delete()

        response = self.query(
            """
            query MyQuery($filters: OrganizationFilterDataInputType) {
              organizationList(filters: $filters) { totalCount results { id name } }
            }
            """,
            variables={"filters": {"excludeDeleted": None}},
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        ids = [o["id"] for o in content["data"]["organizationList"]["results"]]
        self.assertIn(str(removed.id), ids, content)

    def test_explicit_false_excludes_nothing(self):
        """`excludeDeleted: false` must show archived rows, not merely fail to hide them.

        A guard of `if value is not None` would keep absent, null and true correct while
        turning an explicit false into a hide -- so false needs its own case.
        """
        visible = OrganizationFactory.create(name="visible-org")
        removed = OrganizationFactory.create(name="removed-org")
        removed.delete()

        response = self.query(
            """
            query MyQuery($filters: OrganizationFilterDataInputType) {
              organizationList(filters: $filters) { totalCount results { id name } }
            }
            """,
            variables={"filters": {"excludeDeleted": False}},
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        ids = [o["id"] for o in content["data"]["organizationList"]["results"]]
        self.assertIn(str(visible.id), ids, content)
        self.assertIn(str(removed.id), ids, content)

    def test_forward_fk_still_resolves_an_archived_organization(self):
        """contact.organization must not become null once the organization is archived.

        The FK still points at a real row; blanking it loses information the client had.
        """
        org = OrganizationFactory.create(name="soft-deleted-parent")
        contact = ContactFactory.create(organization=org)
        org.delete()
        self.assertIsNotNone(Organization.objects.filter(pk=org.pk).first())

        response = self.query(
            """
            query MyQuery($id: ID!) { contact(id: $id) { id organization { id name } } }
            """,
            variables={"id": str(contact.id)},
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        self.assertIsNotNone(content["data"]["contact"]["organization"], content)
        self.assertEqual(content["data"]["contact"]["organization"]["id"], str(org.id), content)

    def test_m2m_traversal_still_shows_an_archived_organization(self):
        """A plain relation traversal reports the real association, archived or not."""
        country = CountryFactory.create()
        visible = OrganizationFactory.create(name="visible-org")
        removed = OrganizationFactory.create(name="removed-org")
        visible.countries.add(country)
        removed.countries.add(country)
        removed.delete()

        response = self.query(
            """
            query MyQuery($id: ID!) { country(id: $id) { id organizations { id name } } }
            """,
            variables={"id": str(country.id)},
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        ids = [o["id"] for o in content["data"]["country"]["organizations"]]
        self.assertIn(str(visible.id), ids, content)
        self.assertIn(str(removed.id), ids, content)


class TestArchivedOrganizationProvenance(HelixGraphQLTestCase):
    """The provenance paths: an entry's publishers and a figure's sources.

    These reads are the reason nothing hides an archived organization by default: a filtering
    manager removes the row here too, and the association is a fact about a live record that was
    never archived. Both routes are covered -- the single-object route and
    the nested-in-a-list route, which resolve through different loaders -- and `totalCount`
    as well as `results`, because they are computed by separate loaders and only `results`
    would notice a change to one of them.
    """

    def setUp(self) -> None:
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(self.user)
        self.visible = OrganizationFactory.create(name="visible-org")
        self.removed = OrganizationFactory.create(name="removed-org")

    def test_entry_publishers_keep_an_archived_publisher(self):
        entry = EntryFactory.create(created_by=self.user)
        entry.publishers.set([self.visible, self.removed])
        self.removed.delete()

        response = self.query(
            """
            query MyQuery($id: ID!) {
              entry(id: $id) { id publishers { totalCount results { id name } } }
            }
            """,
            variables={"id": str(entry.id)},
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        publishers = content["data"]["entry"]["publishers"]
        ids = [o["id"] for o in publishers["results"]]
        self.assertIn(str(self.visible.id), ids, content)
        self.assertIn(str(self.removed.id), ids, content)
        self.assertEqual(publishers["totalCount"], 2, content)

    def test_entry_publishers_keep_an_archived_publisher_inside_a_list(self):
        """The nested-in-a-list route goes through FilteredRelationListLoader, not the single-object path."""
        entry = EntryFactory.create(created_by=self.user)
        entry.publishers.set([self.visible, self.removed])
        self.removed.delete()

        response = self.query(
            """
            query MyQuery {
              entryList { results { id publishers { totalCount results { id name } } } }
            }
            """,
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        results = content["data"]["entryList"]["results"]
        publishers = next(r["publishers"] for r in results if r["id"] == str(entry.id))
        ids = [o["id"] for o in publishers["results"]]
        self.assertIn(str(self.visible.id), ids, content)
        self.assertIn(str(self.removed.id), ids, content)
        self.assertEqual(publishers["totalCount"], 2, content)

    def test_figure_sources_keep_an_archived_source(self):
        figure = FigureFactory.create(event=EventFactory.create(), created_by=self.user)
        figure.sources.set([self.visible, self.removed])
        self.removed.delete()

        response = self.query(
            """
            query MyQuery($id: ID!) {
              figure(id: $id) { id sources { totalCount results { id name } } }
            }
            """,
            variables={"id": str(figure.id)},
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        sources = content["data"]["figure"]["sources"]
        ids = [o["id"] for o in sources["results"]]
        self.assertIn(str(self.visible.id), ids, content)
        self.assertIn(str(self.removed.id), ids, content)
        self.assertEqual(sources["totalCount"], 2, content)

    def test_a_provenance_list_still_hides_when_asked(self):
        """The argument works on the nested lists too -- the default is off, not absent."""
        entry = EntryFactory.create(created_by=self.user)
        entry.publishers.set([self.visible, self.removed])
        self.removed.delete()

        response = self.query(
            """
            query MyQuery($id: ID!, $filters: OrganizationFilterDataInputType) {
              entry(id: $id) { id publishers(filters: $filters) { results { id name } } }
            }
            """,
            variables={"id": str(entry.id), "filters": {"excludeDeleted": True}},
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        ids = [o["id"] for o in content["data"]["entry"]["publishers"]["results"]]
        self.assertIn(str(self.visible.id), ids, content)
        self.assertNotIn(str(self.removed.id), ids, content)
