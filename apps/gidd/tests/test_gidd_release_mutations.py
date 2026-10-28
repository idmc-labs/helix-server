"""GIDD release authoring: create and update, Admin only.

`is_live` is never an input -- only generation sets it -- and an update records who made it in
`last_modified_by`.
"""

from unittest import mock

from apps.gidd.models import GiddRelease, StatusLog
from apps.gidd.tests.test_generation_lock import run_generation
from apps.users.enums import USER_ROLE
from utils.factories import MonitoringSubRegionFactory, UserFactory
from utils.tests import HelixGraphQLTestCase, HelixTestCase, create_user_with_role

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

UPDATE_GIDD_DATA_MUTATION = """
    mutation UpdateData($releaseId: ID!) {
      giddUpdateData(releaseId: $releaseId) {
        ok
        errors
        result { id status release { id } }
      }
    }
"""


def make_release(**kwargs):
    defaults = dict(name="GIDD", version="1", release_date="2025-05-13", notes="Notes.")
    return GiddRelease.objects.create(**{**defaults, **kwargs})


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


class TestGiddUpdateDataMutation(HelixGraphQLTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.admin = create_user_with_role(
            USER_ROLE.ADMIN.name,
            monitoring_sub_region=MonitoringSubRegionFactory.create().id,
        )
        self.release = make_release()
        self.force_login(self.admin)

    def _trigger(self, release_id):
        with mock.patch("apps.gidd.mutations.update_gidd_data") as task:
            response = self.query(UPDATE_GIDD_DATA_MUTATION, variables={"releaseId": release_id})
        return response, task

    def test_release_is_required(self):
        response = self.query(
            """
            mutation { giddUpdateData { ok } }
            """
        )
        self.assertResponseErrors(response)
        self.assertFalse(StatusLog.objects.exists())

    def test_run_records_its_release(self):
        response, _ = self._trigger(self.release.id)
        self.assertResponseNoErrors(response)
        content = response.json()["data"]["giddUpdateData"]
        self.assertTrue(content["ok"], content)
        self.assertEqual(content["result"]["release"]["id"], str(self.release.id))
        self.assertEqual(StatusLog.objects.get().release, self.release)

    def test_trigger_does_not_mark_release_live(self):
        # Only a successful generation moves the flag, not the request for one.
        self._trigger(self.release.id)
        self.release.refresh_from_db()
        self.assertFalse(self.release.is_live)

    def test_active_run_guard_is_unchanged(self):
        StatusLog.objects.create(triggered_by=self.admin, release=self.release)
        response, task = self._trigger(self.release.id)
        self.assertFalse(response.json()["data"]["giddUpdateData"]["ok"])
        self.assertEqual(StatusLog.objects.count(), 1)
        task.delay.assert_not_called()


class TestGenerationMarksReleaseLive(HelixTestCase):
    def setUp(self) -> None:
        self.user = UserFactory.create()
        self.previous = make_release(version="1", is_live=True)
        self.target = make_release(version="2")

    def _live_ids(self):
        return list(GiddRelease.objects.filter(is_live=True).values_list("id", flat=True))

    def test_success_marks_release_live_and_clears_previous(self):
        log = StatusLog.objects.create(triggered_by=self.user, release=self.target)
        run_generation(log.id)
        log.refresh_from_db()
        self.assertEqual(log.status, StatusLog.Status.SUCCESS)
        self.assertEqual(self._live_ids(), [self.target.id])

    def test_rerun_of_live_release_keeps_it_live(self):
        log = StatusLog.objects.create(triggered_by=self.user, release=self.previous)
        run_generation(log.id)
        self.assertEqual(self._live_ids(), [self.previous.id])

    def test_failed_run_leaves_the_flag_where_it_was(self):
        log = StatusLog.objects.create(triggered_by=self.user, release=self.target)

        def fail():
            raise RuntimeError("generation failed")

        run_generation(log.id, insert_row=fail)
        log.refresh_from_db()
        self.assertEqual(log.status, StatusLog.Status.FAILED)
        self.assertEqual(self._live_ids(), [self.previous.id])

    def test_run_without_release_leaves_the_flag_alone(self):
        # `force_update_gidd_data` and runs logged before releases existed carry no release.
        log = StatusLog.objects.create(triggered_by=self.user)
        run_generation(log.id)
        self.assertEqual(self._live_ids(), [self.previous.id])
