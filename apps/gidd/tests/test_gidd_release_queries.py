"""GIDD release reads: the list, one release by id, the live release, and the run history by release.

The three release queries sit behind login like the rest of the admin schema; any role can read.

Failed runs are listed beside successful ones: a release that took several attempts is a fact
about the release.
"""

from apps.gidd.models import GiddRelease, StatusLog
from apps.users.enums import USER_ROLE
from utils.factories import MonitoringSubRegionFactory
from utils.tests import HelixGraphQLTestCase, create_user_with_role

RELEASES_QUERY = """
    query Releases($filters: GiddReleaseFilterDataInputType, $ordering: String) {
      giddReleases(filters: $filters, ordering: $ordering, page: 1, pageSize: 10) {
        results { id name version }
      }
    }
"""

RELEASE_QUERY = """
    query Release($id: ID!) {
      giddRelease(id: $id) { id name version isLive createdBy { id } }
    }
"""

LIVE_RELEASE_QUERY = """
    query LiveRelease {
      giddLiveRelease { id isLive }
    }
"""

RELEASE_TYPE_FIELDS_QUERY = """
    query {
      __type(name: "GiddReleaseType") { fields { name } }
    }
"""

LOGS_QUERY = """
    query Logs($filters: GiddStatusLogFilterDataInputType) {
      giddLogs(filters: $filters, ordering: "id", page: 1, pageSize: 10) {
        results { id status completedAt release { id } }
      }
    }
"""


class TestGiddReleaseQueries(HelixGraphQLTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.admin = create_user_with_role(
            USER_ROLE.ADMIN.name,
            monitoring_sub_region=MonitoringSubRegionFactory.create().id,
        )
        self.guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.old = self._release(name="GIDD 2024", version="2", release_date="2024-05-01")
        self.live = self._release(name="GIDD 2025", version="3", release_date="2025-05-13", is_live=True)
        self.hidden = self._release(
            name="Draft 2026",
            version="4",
            release_date="2026-09-01",
            is_visible_in_gidd=False,
        )

    def _release(self, **kwargs):
        return GiddRelease.objects.create(notes="Notes.", created_by=self.admin, **kwargs)

    def _releases(self, ordering=None, **filters):
        response = self.query(RELEASES_QUERY, variables={"filters": filters, "ordering": ordering})
        self.assertResponseNoErrors(response)
        return [int(row["id"]) for row in response.json()["data"]["giddReleases"]["results"]]

    # --- access -----------------------------------------------------------------------------

    def test_release_queries_require_login(self):
        for document, variables in (
            (RELEASES_QUERY, {}),
            (RELEASE_QUERY, {"id": self.old.id}),
            (LIVE_RELEASE_QUERY, {}),
        ):
            with self.subTest(document=document):
                self.assertResponseErrors(self.query(document, variables=variables))

    def test_any_role_can_read(self):
        self.force_login(self.guest)
        self.assertResponseNoErrors(self.query(RELEASES_QUERY))
        self.assertResponseNoErrors(self.query(RELEASE_QUERY, variables={"id": self.old.id}))
        self.assertResponseNoErrors(self.query(LIVE_RELEASE_QUERY))

    def test_release_type_publishes_a_named_set_of_fields(self):
        # Pinned, not excluded: a column added to GiddRelease later must not publish itself.
        self.force_login(self.admin)
        response = self.query(RELEASE_TYPE_FIELDS_QUERY)
        self.assertResponseNoErrors(response)
        self.assertEqual(
            {field["name"] for field in response.json()["data"]["__type"]["fields"]},
            {
                "id",
                "name",
                "version",
                "releaseDate",
                "notes",
                "citation",
                "doi",
                "isLive",
                "isVisibleInGidd",
                "createdAt",
                "createdBy",
                "modifiedAt",
                "lastModifiedBy",
            },
        )

    # --- list -------------------------------------------------------------------------------

    def test_list_is_paged(self):
        self.force_login(self.admin)
        response = self.query(
            """
            query { giddReleases(ordering: "id", page: 2, pageSize: 1) { page pageSize results { id } } }
            """
        )
        self.assertResponseNoErrors(response)
        content = response.json()["data"]["giddReleases"]
        self.assertEqual((content["page"], content["pageSize"]), (2, 1))
        self.assertEqual([int(row["id"]) for row in content["results"]], [self.live.id])

    def test_list_is_sortable(self):
        self.force_login(self.admin)
        self.assertEqual(self._releases(ordering="-releaseDate"), [self.live.id, self.old.id])
        self.assertEqual(self._releases(ordering="name"), [self.old.id, self.live.id])

    def test_list_is_filterable(self):
        self.force_login(self.admin)
        self.assertEqual(self._releases(search="2024"), [self.old.id])
        self.assertEqual(self._releases(search="3"), [self.live.id])
        self.assertEqual(self._releases(isLive=True), [self.live.id])
        self.assertEqual(
            self._releases(releaseDateAfter="2025-01-01", releaseDateBefore="2025-12-31"),
            [self.live.id],
        )

    def test_list_hides_releases_hidden_from_gidd(self):
        self.force_login(self.admin)
        self.assertNotIn(self.hidden.id, self._releases(ordering="id"))
        self.assertEqual(self._releases(search="Draft"), [])

    def test_unlisted_ordering_is_refused(self):
        self.force_login(self.admin)
        self.assertResponseErrors(self.query(RELEASES_QUERY, variables={"ordering": "notes"}))

    # --- detail / live ----------------------------------------------------------------------

    def test_release_by_id(self):
        self.force_login(self.admin)
        response = self.query(RELEASE_QUERY, variables={"id": self.old.id})
        self.assertResponseNoErrors(response)
        content = response.json()["data"]["giddRelease"]
        self.assertEqual(content["name"], "GIDD 2024")
        self.assertEqual(content["createdBy"]["id"], str(self.admin.id))

    def test_missing_release_is_null(self):
        self.force_login(self.admin)
        response = self.query(RELEASE_QUERY, variables={"id": 999999})
        self.assertResponseNoErrors(response)
        self.assertIsNone(response.json()["data"]["giddRelease"])

    def test_live_release(self):
        self.force_login(self.admin)
        response = self.query(LIVE_RELEASE_QUERY)
        self.assertResponseNoErrors(response)
        self.assertEqual(response.json()["data"]["giddLiveRelease"], {"id": str(self.live.id), "isLive": True})

    def test_no_live_release_is_null(self):
        GiddRelease.objects.update(is_live=False)
        self.force_login(self.admin)
        response = self.query(LIVE_RELEASE_QUERY)
        self.assertResponseNoErrors(response)
        self.assertIsNone(response.json()["data"]["giddLiveRelease"])

    # --- run history ------------------------------------------------------------------------

    def test_run_history_requires_login(self):
        self.assertResponseErrors(self.query(LOGS_QUERY))

    def test_run_history_filters_by_release_and_keeps_failed_runs(self):
        failed = StatusLog.objects.create(
            triggered_by=self.admin,
            release=self.live,
            status=StatusLog.Status.FAILED,
        )
        succeeded = StatusLog.objects.create(
            triggered_by=self.admin,
            release=self.live,
            status=StatusLog.Status.SUCCESS,
        )
        StatusLog.objects.create(triggered_by=self.admin, release=self.old, status=StatusLog.Status.SUCCESS)
        StatusLog.objects.create(triggered_by=self.admin, status=StatusLog.Status.SUCCESS)

        self.force_login(self.admin)
        response = self.query(LOGS_QUERY, variables={"filters": {"releases": [self.live.id]}})
        self.assertResponseNoErrors(response)
        rows = response.json()["data"]["giddLogs"]["results"]
        self.assertEqual([int(row["id"]) for row in rows], [failed.id, succeeded.id])
        self.assertEqual([row["status"] for row in rows], ["FAILED", "SUCCESS"])
        self.assertEqual({row["release"]["id"] for row in rows}, {str(self.live.id)})
