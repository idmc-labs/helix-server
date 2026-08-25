from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.crisis.models import Crisis
from apps.gidd.cache import GiddExportCache
from apps.gidd.models import (
    GiddDisplacement,
    GiddEventDisplacement,
    ReleaseMetadata,
    StatusLog,
)
from helix.caches import external_api_cache
from utils.factories import (
    ClientFactory,
    CountryFactory,
    DisasterCategoryFactory,
    DisasterSubCategoryFactory,
    DisasterSubTypeFactory,
    DisasterTypeFactory,
    UserFactory,
)
from utils.tests import HelixTestCase


class GiddCacheTestMixin:
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory.create()
        cls.country = CountryFactory.create(iso3="AFG", idmc_short_name="Afghanistan")
        hazard_category = DisasterCategoryFactory.create(name="Natural")
        hazard_sub_category = DisasterSubCategoryFactory.create(name="Geophysical", category=hazard_category)
        hazard_type = DisasterTypeFactory.create(name="Earthquake", disaster_sub_category=hazard_sub_category)
        cls.hazard_sub_type = DisasterSubTypeFactory.create(name="Ground shaking", type=hazard_type)
        cls.hazard_type = hazard_type
        cls.hazard_category = hazard_category
        cls.hazard_sub_category = hazard_sub_category

    def setUp(self):
        super().setUp()
        ReleaseMetadata.objects.create(
            release_year=2024,
            pre_release_year=2025,
            modified_by=self.user,
        )
        StatusLog.objects.create(
            triggered_by=self.user,
            triggered_at=timezone.now(),
            completed_at=timezone.now(),
            status=StatusLog.Status.SUCCESS,
        )


class TestGiddHelperWarmup(GiddCacheTestMixin, HelixTestCase):
    CLIENT_CODE = "warmup-client"

    def setUp(self):
        super().setUp()
        self.gidd_client = ClientFactory.create(code=self.CLIENT_CODE, is_active=True)
        external_api_cache.set("client_ids", [self.CLIENT_CODE], None)

    def tearDown(self):
        external_api_cache.delete("client_ids")
        super().tearDown()

    @patch("apps.gidd.management.commands.gidd_helper.VIEW_MAP")
    def test_warm_all_presets(self, mock_view_map):
        mock_view = MagicMock()
        mock_view.return_value = MagicMock(status_code=302)
        mock_view_map.__getitem__ = lambda self, key: (mock_view, f"/api/fake/{key}/")
        mock_view_map.__iter__ = lambda self: iter(
            [
                GiddExportCache.Key.DISASTER_EXPORT,
                GiddExportCache.Key.DISPLACEMENT_EXPORT,
                GiddExportCache.Key.DISAGGREGATION_EXPORT,
                GiddExportCache.Key.DISAGGREGATION_EXPORT_GEOJSON,
            ]
        )

        out = StringIO()
        call_command("gidd_helper", "warmup", "--client-id", self.CLIENT_CODE, stdout=out)
        output = out.getvalue()

        self.assertIn("disaster-export", output)
        self.assertIn("displacement-export", output)
        self.assertIn("disaggregation-export", output)
        self.assertIn("disaggregation-export-geojson", output)
        self.assertEqual(mock_view.call_count, 4)

    @patch("apps.gidd.management.commands.gidd_helper.VIEW_MAP")
    def test_warm_single_key(self, mock_view_map):
        mock_view = MagicMock()
        mock_view.return_value = MagicMock(status_code=302)
        mock_view_map.__getitem__ = lambda self, key: (mock_view, "/api/fake/")

        out = StringIO()
        call_command("gidd_helper", "warmup", "--client-id", self.CLIENT_CODE, "--key", "disaster-export", stdout=out)
        output = out.getvalue()

        self.assertIn("disaster-export", output)
        self.assertEqual(mock_view.call_count, 1)

    @patch("apps.gidd.management.commands.gidd_helper.VIEW_MAP")
    def test_warm_with_custom_filters(self, mock_view_map):
        mock_view = MagicMock()
        mock_view.return_value = MagicMock(status_code=302)
        mock_view_map.__getitem__ = lambda self, key: (mock_view, "/api/fake/")

        out = StringIO()
        call_command(
            "gidd_helper",
            "warmup",
            "--client-id",
            self.CLIENT_CODE,
            "--key",
            "disaster-export",
            "--filters",
            '{"iso3": "AFG", "start_year": "2023"}',
            stdout=out,
        )

        request = mock_view.call_args[0][0]
        self.assertEqual(request.GET["iso3"], "AFG")
        self.assertEqual(request.GET["start_year"], "2023")
        self.assertEqual(request.GET["client_id"], self.CLIENT_CODE)

    def test_warm_invalid_json_filters(self):
        err = StringIO()
        call_command("gidd_helper", "warmup", "--client-id", self.CLIENT_CODE, "--filters", "not json", stderr=err)
        self.assertIn("Invalid JSON", err.getvalue())

    @patch("apps.gidd.management.commands.gidd_helper.VIEW_MAP")
    def test_warm_handles_exception(self, mock_view_map):
        mock_view = MagicMock(side_effect=RuntimeError("boom"))
        mock_view_map.__getitem__ = lambda self, key: (mock_view, "/api/fake/")

        out = StringIO()
        call_command("gidd_helper", "warmup", "--client-id", self.CLIENT_CODE, "--key", "disaster-export", stdout=out)
        self.assertIn("FAIL", out.getvalue())
        self.assertIn("boom", out.getvalue())

    def test_warm_missing_client_id(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("gidd_helper", "warmup")

    def test_warm_invalid_client_id(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError) as ctx:
            call_command("gidd_helper", "warmup", "--client-id", "bogus-client")
        self.assertIn("not active", str(ctx.exception))


class TestGiddHelperClear(GiddCacheTestMixin, HelixTestCase):
    """
    Cache layout under listdir:
        gidd-cache-export/
            2024-01-01-00-00-00/
                disaster-export/
                    abc123/
                        IDMC_GIDD_Disasters.xlsx
                        IDMC_GIDD_Disasters.xlsx.json
                displacement-export/
                    def456/
                        IDMC_GIDD_Displacements.xlsx
                        IDMC_GIDD_Displacements.xlsx.json
    """

    BASE = "gidd-cache-export"
    DATE_A = "2024-01-01-00-00-00"
    DATE_B = "2025-01-01-00-00-00"

    def _build_listdir(self):
        tree = {
            self.BASE: ([self.DATE_A, self.DATE_B], []),
            f"{self.BASE}/{self.DATE_A}": (["disaster-export", "displacement-export"], []),
            f"{self.BASE}/{self.DATE_A}/disaster-export": (["abc"], []),
            f"{self.BASE}/{self.DATE_A}/disaster-export/abc": ([], ["d.xlsx", "d.xlsx.json"]),
            f"{self.BASE}/{self.DATE_A}/displacement-export": (["def"], []),
            f"{self.BASE}/{self.DATE_A}/displacement-export/def": ([], ["dd.xlsx", "dd.xlsx.json"]),
            f"{self.BASE}/{self.DATE_B}": (["disaster-export"], []),
            f"{self.BASE}/{self.DATE_B}/disaster-export": (["ghi"], []),
            f"{self.BASE}/{self.DATE_B}/disaster-export/ghi": ([], ["d2.xlsx", "d2.xlsx.json"]),
        }

        def listdir(prefix):
            return tree.get(prefix.rstrip("/"), ([], []))

        return listdir

    @patch("apps.gidd.management.commands.gidd_helper.external_storage")
    def test_clear_all_with_yes(self, mock_storage):
        mock_storage.listdir.side_effect = self._build_listdir()

        out = StringIO()
        call_command("gidd_helper", "clear", "--yes", stdout=out)

        deleted = [c.args[0] for c in mock_storage.delete.call_args_list]
        self.assertEqual(len(deleted), 6)
        self.assertIn(self.DATE_A, deleted[0])
        self.assertIn("Deleted 6/6", out.getvalue())

    @patch("apps.gidd.management.commands.gidd_helper.external_storage")
    def test_clear_by_key(self, mock_storage):
        mock_storage.listdir.side_effect = self._build_listdir()

        out = StringIO()
        call_command("gidd_helper", "clear", "--key", "disaster-export", "--yes", stdout=out)

        deleted = [c.args[0] for c in mock_storage.delete.call_args_list]
        self.assertEqual(len(deleted), 4)
        for path in deleted:
            self.assertIn("disaster-export", path)
            self.assertNotIn("displacement-export", path)

    @patch("apps.gidd.management.commands.gidd_helper.external_storage")
    def test_clear_by_status_log_id(self, mock_storage):
        mock_storage.listdir.side_effect = self._build_listdir()

        completed_at = timezone.datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        log = StatusLog.objects.create(
            triggered_by=self.user,
            triggered_at=completed_at,
            completed_at=completed_at,
            status=StatusLog.Status.SUCCESS,
        )

        out = StringIO()
        call_command("gidd_helper", "clear", "--status-log-id", str(log.id), "--yes", stdout=out)

        deleted = [c.args[0] for c in mock_storage.delete.call_args_list]
        self.assertEqual(len(deleted), 4)
        for path in deleted:
            self.assertIn(self.DATE_A, path)
            self.assertNotIn(self.DATE_B, path)

    @patch("apps.gidd.management.commands.gidd_helper.external_storage")
    def test_clear_dry_run(self, mock_storage):
        mock_storage.listdir.side_effect = self._build_listdir()

        out = StringIO()
        call_command("gidd_helper", "clear", "--dry-run", stdout=out)

        self.assertEqual(mock_storage.delete.call_count, 0)
        self.assertIn("Dry run", out.getvalue())

    @patch("builtins.input", return_value="n")
    @patch("apps.gidd.management.commands.gidd_helper.external_storage")
    def test_clear_prompt_aborts(self, mock_storage, mock_input):
        mock_storage.listdir.side_effect = self._build_listdir()

        out = StringIO()
        call_command("gidd_helper", "clear", stdout=out)

        self.assertEqual(mock_storage.delete.call_count, 0)
        self.assertIn("Aborted", out.getvalue())

    @patch("apps.gidd.management.commands.gidd_helper.external_storage")
    def test_clear_invalid_status_log_id(self, mock_storage):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("gidd_helper", "clear", "--status-log-id", "999999", "--yes")

    @patch("apps.gidd.management.commands.gidd_helper.external_storage")
    def test_clear_no_paths_found(self, mock_storage):
        mock_storage.listdir.return_value = ([], [])

        out = StringIO()
        call_command("gidd_helper", "clear", "--yes", stdout=out)

        self.assertEqual(mock_storage.delete.call_count, 0)
        self.assertIn("No cached files", out.getvalue())


class TestGiddHelperStatusLogs(GiddCacheTestMixin, HelixTestCase):
    def test_list_status_logs_default_limit(self):
        for i in range(7):
            StatusLog.objects.create(
                triggered_by=self.user,
                triggered_at=timezone.now(),
                completed_at=timezone.now(),
                status=StatusLog.Status.SUCCESS,
            )

        out = StringIO()
        call_command("gidd_helper", "status-logs", stdout=out)
        output = out.getvalue()

        self.assertIn("ID", output)
        self.assertIn("Status", output)
        self.assertIn("SUCCESS", output)
        self.assertEqual(output.count("SUCCESS"), 5)

    def test_list_status_logs_custom_limit(self):
        for _ in range(4):
            StatusLog.objects.create(
                triggered_by=self.user,
                triggered_at=timezone.now(),
                completed_at=timezone.now(),
                status=StatusLog.Status.SUCCESS,
            )

        out = StringIO()
        call_command("gidd_helper", "status-logs", "--limit", "2", stdout=out)
        output = out.getvalue()

        self.assertEqual(output.count("SUCCESS"), 2)

    def test_list_status_logs_marks_current(self):
        out = StringIO()
        call_command("gidd_helper", "status-logs", stdout=out)
        self.assertIn("<- current", out.getvalue())

    def test_list_status_logs_empty(self):
        StatusLog.objects.all().delete()

        out = StringIO()
        call_command("gidd_helper", "status-logs", stdout=out)
        self.assertIn("No StatusLog entries", out.getvalue())


class TestGiddHelperClients(GiddCacheTestMixin, HelixTestCase):
    def tearDown(self):
        external_api_cache.delete("client_ids")
        super().tearDown()

    def test_list_clients_with_active(self):
        c1 = ClientFactory.create(code="abc-1", name="Alpha", is_active=True)
        c2 = ClientFactory.create(code="abc-2", name="Beta", is_active=True)
        external_api_cache.set("client_ids", [c1.code, c2.code], None)

        out = StringIO()
        call_command("gidd_helper", "clients", stdout=out)
        output = out.getvalue()

        self.assertIn("abc-1", output)
        self.assertIn("Alpha", output)
        self.assertIn("abc-2", output)
        self.assertIn("Beta", output)

    def test_list_clients_empty(self):
        external_api_cache.delete("client_ids")

        out = StringIO()
        call_command("gidd_helper", "clients", stdout=out)
        self.assertIn("No active client_ids", out.getvalue())

    def test_list_clients_handles_missing_db_record(self):
        external_api_cache.set("client_ids", ["orphan-code"], None)

        out = StringIO()
        call_command("gidd_helper", "clients", stdout=out)
        output = out.getvalue()

        self.assertIn("orphan-code", output)
        self.assertIn("(not in DB)", output)


@patch("apps.gidd.views.track_gidd", return_value=None)
class TestGiddExportCacheAPI(GiddCacheTestMixin, HelixTestCase):
    DISASTER_EXPORT_URL = "/external-api/gidd/disasters/disaster-export/"
    DISPLACEMENT_EXPORT_URL = "/external-api/gidd/displacements/displacement-export/"

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        GiddEventDisplacement.objects.create(
            cause=Crisis.CRISIS_TYPE.DISASTER,
            country=self.country,
            iso3="AFG",
            country_name="Afghanistan",
            year=2024,
            new_displacement=1000,
            new_displacement_rounded=1000,
            event_name="Test Earthquake",
            hazard_category=self.hazard_category,
            hazard_sub_category=self.hazard_sub_category,
            hazard_type=self.hazard_type,
            hazard_sub_type=self.hazard_sub_type,
            hazard_category_name="Natural",
            hazard_sub_category_name="Geophysical",
            hazard_type_name="Earthquake",
            hazard_sub_type_name="Ground shaking",
        )
        GiddDisplacement.objects.create(
            cause=Crisis.CRISIS_TYPE.DISASTER,
            country=self.country,
            iso3="AFG",
            country_name="Afghanistan",
            year=2024,
            new_displacement=1000,
            new_displacement_rounded=1000,
        )

    @patch("apps.gidd.cache.external_storage")
    def test_disaster_export_first_call_generates_cache(self, mock_storage, mock_track):
        mock_storage.exists.return_value = False
        mock_storage.save.return_value = None
        mock_storage.url.return_value = "/fake-s3/cached-file.xlsx"

        response = self.client.get(self.DISASTER_EXPORT_URL)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(mock_storage.save.call_count, 2)

        file_call, metadata_call = mock_storage.save.call_args_list
        self.assertIn("disaster-export", file_call[0][0])
        self.assertTrue(metadata_call[0][0].endswith(".json"))

    @patch("apps.gidd.cache.external_storage")
    def test_disaster_export_second_call_uses_cache(self, mock_storage, mock_track):
        mock_storage.exists.return_value = False
        mock_storage.save.return_value = None
        mock_storage.url.return_value = "/fake-s3/cached-file.xlsx"

        self.client.get(self.DISASTER_EXPORT_URL)
        initial_save_count = mock_storage.save.call_count

        mock_storage.exists.return_value = True

        self.client.get(self.DISASTER_EXPORT_URL)
        self.assertEqual(mock_storage.save.call_count, initial_save_count)

    @override_settings(GIDD_EXPORT_CACHE_DISABLED=True)
    @patch("apps.gidd.cache.external_storage")
    def test_disaster_export_streams_file_when_cache_disabled(self, mock_storage, mock_track):
        # When disabled, storage is bypassed entirely and the file is streamed directly.
        response = self.client.get(self.DISASTER_EXPORT_URL)
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(mock_storage.exists.call_count, 0)
        self.assertEqual(mock_storage.save.call_count, 0)

    @patch("apps.gidd.cache.external_storage")
    def test_displacement_export_first_call_generates_cache(self, mock_storage, mock_track):
        mock_storage.exists.return_value = False
        mock_storage.save.return_value = None
        mock_storage.url.return_value = "/fake-s3/cached-file.xlsx"

        response = self.client.get(self.DISPLACEMENT_EXPORT_URL)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(mock_storage.save.call_count, 2)

        file_call, metadata_call = mock_storage.save.call_args_list
        self.assertIn("displacement-export", file_call[0][0])
        self.assertTrue(metadata_call[0][0].endswith(".json"))

    @patch("apps.gidd.cache.external_storage")
    def test_displacement_export_second_call_uses_cache(self, mock_storage, mock_track):
        mock_storage.exists.return_value = False
        mock_storage.save.return_value = None
        mock_storage.url.return_value = "/fake-s3/cached-file.xlsx"

        self.client.get(self.DISPLACEMENT_EXPORT_URL)
        initial_save_count = mock_storage.save.call_count

        mock_storage.exists.return_value = True

        self.client.get(self.DISPLACEMENT_EXPORT_URL)
        self.assertEqual(mock_storage.save.call_count, initial_save_count)

    @patch("apps.gidd.cache.external_storage")
    def test_different_filters_produce_different_cache_keys(self, mock_storage, mock_track):
        mock_storage.exists.return_value = False
        mock_storage.save.return_value = None
        mock_storage.url.return_value = "/fake-s3/cached-file.xlsx"

        self.client.get(self.DISASTER_EXPORT_URL)
        first_cache_key = mock_storage.save.call_args_list[0][0][0]

        mock_storage.reset_mock()
        mock_storage.exists.return_value = False

        self.client.get(self.DISASTER_EXPORT_URL, {"start_year": "2023"})
        second_cache_key = mock_storage.save.call_args_list[0][0][0]

        self.assertNotEqual(first_cache_key, second_cache_key)
