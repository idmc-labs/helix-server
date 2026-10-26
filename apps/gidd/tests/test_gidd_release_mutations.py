"""GIDD release authoring: create and update, Admin only.

`is_live` is never an input -- only generation sets it -- and an update records who made it in
`last_modified_by`.
"""

from apps.gidd.models import GiddRelease
from apps.users.enums import USER_ROLE
from utils.factories import MonitoringSubRegionFactory
from utils.tests import HelixGraphQLTestCase, create_user_with_role

CREATE_MUTATION = """
    mutation CreateRelease($data: GiddReleaseCreateInputType!) {
      createGiddRelease(data: $data) {
        ok
        errors
        result { id name version releaseDate notes citation isLive isVisibleInGidd }
      }
    }
"""

UPDATE_MUTATION = """
    mutation UpdateRelease($data: GiddReleaseUpdateInputType!) {
      updateGiddRelease(data: $data) {
        ok
        errors
        result { id name notes isLive isVisibleInGidd lastModifiedBy { id } }
      }
    }
"""

RELEASE_INPUT = {
    "name": "GIDD 2026",
    "version": "4",
    "releaseDate": "2026-09-01",
    "notes": "Historical data revision project.",
    "citation": "IDMC (2026). Global Internal Displacement Database.",
}


class TestGiddReleaseMutations(HelixGraphQLTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.admin = create_user_with_role(
            USER_ROLE.ADMIN.name,
            monitoring_sub_region=MonitoringSubRegionFactory.create().id,
        )

    def _create(self, **overrides):
        return self.query(CREATE_MUTATION, variables={"data": {**RELEASE_INPUT, **overrides}})

    def _update(self, **data):
        return self.query(UPDATE_MUTATION, variables={"data": data})

    def _release(self, **kwargs):
        return GiddRelease.objects.create(
            name="GIDD 2025",
            version="3.0",
            release_date="2025-05-13",
            notes="Added May 2025 revision round.",
            created_by=self.admin,
            **kwargs,
        )

    # --- create -----------------------------------------------------------------------------

    def test_admin_creates_a_release(self):
        self.force_login(self.admin)
        response = self._create()
        self.assertResponseNoErrors(response)
        content = response.json()["data"]["createGiddRelease"]
        self.assertTrue(content["ok"], content)
        self.assertEqual(content["result"]["version"], "4")
        self.assertFalse(content["result"]["isLive"])
        self.assertTrue(content["result"]["isVisibleInGidd"])
        release = GiddRelease.objects.get(id=content["result"]["id"])
        self.assertEqual(release.created_by, self.admin)

    def test_is_live_is_not_an_input(self):
        self.force_login(self.admin)
        response = self._create(isLive=True)
        self.assertResponseErrors(response)
        self.assertFalse(GiddRelease.objects.exists())

    def test_create_requires_the_authored_fields(self):
        self.force_login(self.admin)
        data = {k: v for k, v in RELEASE_INPUT.items() if k != "notes"}
        response = self.query(CREATE_MUTATION, variables={"data": data})
        self.assertResponseErrors(response)
        self.assertFalse(GiddRelease.objects.exists())

    def test_a_new_release_starts_empty(self):
        """No copy-over: the changelog is assembled from every release, so nothing is inherited."""
        self._release(citation="Old citation")
        self.force_login(self.admin)
        response = self._create(citation=None)
        self.assertResponseNoErrors(response)
        content = response.json()["data"]["createGiddRelease"]
        self.assertIsNone(content["result"]["citation"])

    # --- update -----------------------------------------------------------------------------

    def test_admin_edits_authored_text(self):
        release = self._release()
        self.force_login(self.admin)
        response = self._update(id=release.id, notes="Corrected note.")
        self.assertResponseNoErrors(response)
        content = response.json()["data"]["updateGiddRelease"]
        self.assertTrue(content["ok"], content)
        release.refresh_from_db()
        self.assertEqual(release.notes, "Corrected note.")
        self.assertEqual(release.name, "GIDD 2025")
        self.assertEqual(release.last_modified_by, self.admin)

    def test_visibility_change_records_who_changed_it(self):
        release = self._release()
        self.force_login(self.admin)
        response = self._update(id=release.id, isVisibleInGidd=False)
        self.assertResponseNoErrors(response)
        content = response.json()["data"]["updateGiddRelease"]
        self.assertTrue(content["ok"], content)
        self.assertEqual(content["result"]["lastModifiedBy"]["id"], str(self.admin.id))
        release.refresh_from_db()
        self.assertFalse(release.is_visible_in_gidd)
        self.assertEqual(release.last_modified_by, self.admin)

    def test_update_cannot_set_is_live(self):
        release = self._release()
        self.force_login(self.admin)
        response = self._update(id=release.id, isLive=True)
        self.assertResponseErrors(response)
        release.refresh_from_db()
        self.assertFalse(release.is_live)

    def test_update_of_a_missing_release_errors(self):
        self.force_login(self.admin)
        response = self._update(id=999999, notes="x")
        self.assertResponseNoErrors(response)
        content = response.json()["data"]["updateGiddRelease"]
        self.assertFalse(content["ok"])

    # --- permission -------------------------------------------------------------------------

    def test_only_admin_can_create_or_update(self):
        release = self._release()
        for role in (
            USER_ROLE.REGIONAL_COORDINATOR,
            USER_ROLE.MONITORING_EXPERT,
            USER_ROLE.DIRECTORS_OFFICE,
            USER_ROLE.REPORTING_TEAM,
            USER_ROLE.GUEST,
        ):
            with self.subTest(role=role.name):
                user = create_user_with_role(
                    role.name,
                    monitoring_sub_region=MonitoringSubRegionFactory.create().id,
                )
                self.force_login(user)
                self.assertResponseErrors(self._create())
                self.assertResponseErrors(self._update(id=release.id, notes="x"))
        self.assertEqual(GiddRelease.objects.count(), 1)
        release.refresh_from_db()
        self.assertEqual(release.notes, "Added May 2025 revision round.")

    def test_anonymous_is_refused(self):
        self.assertResponseErrors(self._create())
        self.assertFalse(GiddRelease.objects.exists())
