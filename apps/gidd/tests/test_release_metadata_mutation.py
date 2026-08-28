"""Saving the release metadata must not regenerate GIDD.

The metadata is a filter applied over already-generated rows — `apps/gidd/tasks.py` never
reads it — so a metadata edit needs no rebuild. Triggering one made every edit cost a full
delete-and-rebuild of the GIDD tables, and it is what put a pending run behind an operation
that cannot affect it.
"""

from unittest.mock import patch

from apps.gidd.models import ReleaseMetadata, StatusLog
from apps.users.enums import USER_ROLE
from utils.factories import MonitoringSubRegionFactory
from utils.tests import HelixGraphQLTestCase, create_user_with_role

MUTATION = """
    mutation MyMutation($data: ReleaseMetadataInputType!) {
      giddUpdateReleaseMetaData(data: $data) {
        ok
        errors
        result { releaseYear preReleaseYear }
      }
    }
"""


class TestGiddUpdateReleaseMetaData(HelixGraphQLTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.editor = create_user_with_role(
            USER_ROLE.ADMIN.name,
            monitoring_sub_region=MonitoringSubRegionFactory.create().id,
        )
        self.force_login(self.editor)

    def _run(self):
        return self.query(MUTATION, variables={"data": {"releaseYear": 2023, "preReleaseYear": 2024}})

    def test_saving_metadata_does_not_enqueue_a_generation(self):
        with patch("apps.gidd.mutations.update_gidd_data") as task:
            response = self._run()
        self.assertResponseNoErrors(response)
        content = response.json()["data"]["giddUpdateReleaseMetaData"]
        self.assertTrue(content["ok"], content)
        task.delay.assert_not_called()

    def test_saving_metadata_creates_no_status_log(self):
        """A metadata edit is not a run, so it must not leave a StatusLog behind.

        The previous version created one and passed the ReleaseMetadata id as `log_id`, so a
        run's SUCCESS/FAILED landed on an unrelated row.
        """
        before = StatusLog.objects.count()
        with patch("apps.gidd.mutations.update_gidd_data"):
            self.assertResponseNoErrors(self._run())
        self.assertEqual(StatusLog.objects.count(), before)

    def test_the_saved_metadata_is_active_immediately(self):
        """No gating on a successful run: the newest row is what the public filters read."""
        with patch("apps.gidd.mutations.update_gidd_data"):
            self.assertResponseNoErrors(self._run())
        latest = ReleaseMetadata.objects.last()
        self.assertEqual((latest.release_year, latest.pre_release_year), (2023, 2024))
