import json
from datetime import timedelta

from rest_framework import status
from rest_framework.exceptions import PermissionDenied

from apps.contrib.models import Client, ClientTrackInfo
from apps.contrib.tasks import (
    generate_idu_options_dump_file,
    generate_idus_all_disaster_dump_file,
    generate_idus_all_dump_file,
    generate_idus_dump_file,
    save_and_delete_tracked_data_from_redis_to_db,
)
from apps.entry.models import ExternalApiDump
from helix.caches import external_api_cache
from utils.common import track_gidd
from utils.factories import (
    ClientFactory,
    CountryFactory,
    DisasterSubTypeFactory,
    DisasterTypeFactory,
    GeographicalGroupFactory,
    ViolenceFactory,
    ViolenceSubTypeFactory,
)
from utils.tests import HelixAPITestCase

# All IDU exports: each dataset (last-180-days, all, all/disaster) is served as
# json, excel and geojson.
IDU_EXPORT_URLS = [
    "/external-api/idus/last-180-days/",
    "/external-api/idus/last-180-days-excel/",
    "/external-api/idus/last-180-days-geojson/",
    "/external-api/idus/all/",
    "/external-api/idus/all-excel/",
    "/external-api/idus/all-geojson/",
    "/external-api/idus/all/disaster/",
    "/external-api/idus/all/disaster-excel/",
    "/external-api/idus/all/disaster-geojson/",
]

IDU_REFERENCES_URL = "/external-api/idus/references/"

GIDD_API_URLS = [
    "/external-api/gidd/countries/",
    "/external-api/gidd/conflicts/",
    "/external-api/gidd/disasters/",
    "/external-api/gidd/displacements/",
    "/external-api/gidd/public-figure-analyses/",
    # GIDD exports
    "/external-api/gidd/disasters/disaster-export/",
    "/external-api/gidd/displacements/displacement-export/",
    "/external-api/gidd/disaggregations/disaggregation-geojson/",
    "/external-api/gidd/disaggregations/disaggregation-export/",
]

EXTERNAL_API_URLS = [*IDU_EXPORT_URLS, IDU_REFERENCES_URL, *GIDD_API_URLS]


class TestExternalClientTrack(HelixAPITestCase):
    def setUp(self):
        super().setUp()
        self.client1 = ClientFactory.create(code="random-code-1", is_active=True, share_source=True)
        self.client2 = ClientFactory.create(code="random-code-2", is_active=True, share_source=True)

    def test_tracking_enforced_on_idu_and_gidd_rest_apis(self):
        # Every external API endpoint must run track_gidd and reject unregistered clients.
        # NOTE: a 403 response status for an unregistered client means tracking is implemented.
        unregistered_client_id = "unregistered-client-code"
        for endpoint in EXTERNAL_API_URLS:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(f"{endpoint}?client_id={unregistered_client_id}")
                self.assertEqual(
                    response.status_code,
                    status.HTTP_403_FORBIDDEN,
                    f"{endpoint} did not enforce client tracking (track_gidd)",
                )

    def test_should_return_idu_data_or_404_for_registered_clients(self):
        # All IDU exports must behave the same across their lifecycle.
        endpoints = [f"{url}?client_id={self.client1.code}" for url in IDU_EXPORT_URLS]

        def _response_status_check(status_code):
            for endpoint in endpoints:
                with self.subTest(endpoint=endpoint, expected=status_code):
                    response = self.client.get(endpoint)
                    self.assertEqual(response.status_code, status_code)

        # Case: IDU data is not present
        self.assertEqual(ExternalApiDump.objects.count(), 0)
        _response_status_check(status.HTTP_404_NOT_FOUND)

        # IDU data has been generarted
        generate_idus_dump_file()
        generate_idus_all_dump_file()
        generate_idus_all_disaster_dump_file()
        _response_status_check(status.HTTP_302_FOUND)

        # IDU data generation is in progress
        ExternalApiDump.objects.update(
            status=ExternalApiDump.Status.PENDING,
            dump_file=None,
        )
        _response_status_check(status.HTTP_202_ACCEPTED)

    def test_idu_tracked_data(self):
        # Each IDU export is tracked as a distinct api type, so every export is
        # hit for both clients.
        endpoints = [f"{url}?client_id={client.code}" for client in [self.client1, self.client2] for url in IDU_EXPORT_URLS]
        expected_track_count = len(IDU_EXPORT_URLS) * 2

        # Assume yesterdays data
        self.now_mock.return_value = self.now_datetime - timedelta(days=1)
        for endpoint in endpoints:
            self.client.get(endpoint)

        # Sync redis data to database
        save_and_delete_tracked_data_from_redis_to_db()
        self.assertEqual(ClientTrackInfo.objects.count(), expected_track_count)

        # Again track client ids for same date
        for endpoint in endpoints:
            self.client.get(endpoint)

        # Resync redis data for same date
        save_and_delete_tracked_data_from_redis_to_db()
        self.assertEqual(ClientTrackInfo.objects.count(), expected_track_count)

        # Again track client ids for same date
        for endpoint in endpoints:
            self.client.get(endpoint)

        # Resync redis data for same date
        save_and_delete_tracked_data_from_redis_to_db()
        self.assertEqual(ClientTrackInfo.objects.count(), expected_track_count)

        # For each client track info requests per day should be 1 for each api type
        for obj in ClientTrackInfo.objects.all():
            self.assertEqual(obj.requests_per_day, 3)

    def test_should_update_duplicated_tracking_record(self):
        # Create duplicated redis client tracking keys
        keys = [
            "trackinfo:2022-07-09:idus",
            "trackinfo:2022-07-12:idus",
            "trackinfo:2022-07-28:idus",
            "trackinfo:2022-07-05:idus",
            "trackinfo:2022-07-04:idus",
            "trackinfo:2022-07-01:idus",
            "trackinfo:2022-07-06:idus",
            "trackinfo:2022-08-01:idus",
            "trackinfo:2022-08-02:idus",
            "trackinfo:2022-07-14:idus",
            "trackinfo:2022-07-03:idus",
            "trackinfo:2022-07-13:idus",
            "trackinfo:2022-07-02:idus",
            "trackinfo:2022-07-07:idus",
        ]
        for key in keys:
            external_api_cache.set(f"{key}:{self.client1.code}", 100, None)

        # Trigger task
        save_and_delete_tracked_data_from_redis_to_db()
        self.assertEqual(ClientTrackInfo.objects.count(), 14)

        for key in keys:
            external_api_cache.set(f"{key}:{self.client1.code}", 100, None)

        # Trigger task
        save_and_delete_tracked_data_from_redis_to_db()
        self.assertEqual(ClientTrackInfo.objects.count(), 14)

    def test_gidd_tracked_data(self):
        # Each GIDD endpoint is tracked as a distinct api type, so every endpoint
        # is hit for both clients.
        endpoints = [f"{url}?client_id={client.code}" for client in [self.client1, self.client2] for url in GIDD_API_URLS]
        expected_track_count = len(GIDD_API_URLS) * 2

        # Assume yesterdays data
        self.now_mock.return_value = self.now_datetime - timedelta(days=1)
        for endpoint in endpoints:
            self.client.get(endpoint)

        # Sync redis data to database
        save_and_delete_tracked_data_from_redis_to_db()
        self.assertEqual(ClientTrackInfo.objects.count(), expected_track_count)

        # Again track client ids for same date
        for endpoint in endpoints:
            self.client.get(endpoint)

        # Resync redis data for same date
        save_and_delete_tracked_data_from_redis_to_db()
        self.assertEqual(ClientTrackInfo.objects.count(), expected_track_count)

        # Again track client ids for same date
        for endpoint in endpoints:
            self.client.get(endpoint)

        # Resync redis data for same date
        save_and_delete_tracked_data_from_redis_to_db()
        self.assertEqual(ClientTrackInfo.objects.count(), expected_track_count)

        # For each client track info requests per day should be 1 for each api type
        for obj in ClientTrackInfo.objects.all():
            self.assertEqual(obj.requests_per_day, 3)


class TestTrackGiddWithMissingClientRow(HelixAPITestCase):
    """A code that is in the redis registry but whose `Client` row is gone.

    `track_gidd` gates every external endpoint. It checks the code against the `client_ids`
    redis registry first, then loads the row -- and the two can disagree, because only
    `Client.save()`/`Client.delete()` refresh the registry. A queryset or admin bulk delete
    bypasses both, leaving codes in redis with no row behind them; `client.is_active` then
    raised `AttributeError` on a public unauthenticated endpoint (a 500 where 403 is the
    correct and already-implemented answer).

    A code that was never registered stops at the registry check and never loads a row, so
    only a registered-then-orphaned code reaches this branch.
    """

    MISSING_CODE = "registered-but-deleted"
    LIVE_CODE = "registered-and-present"
    INACTIVE_CODE = "registered-but-inactive"

    def setUp(self):
        super().setUp()
        # ClientFactory.create() -> Client.save() -> the registry is rewritten from the
        # table, so all three codes are registered at this point.
        deleted = ClientFactory.create(code=self.MISSING_CODE, is_active=True)
        self.live_client = ClientFactory.create(code=self.LIVE_CODE, is_active=True)
        ClientFactory.create(code=self.INACTIVE_CODE, is_active=False)
        # A queryset delete does NOT go through Client.delete(), so the registry keeps the
        # code. This is exactly how the rows disappear in production.
        Client.objects.filter(pk=deleted.pk).delete()
        self.assertIn(self.MISSING_CODE, external_api_cache.get("client_ids"))
        self.assertFalse(Client.objects.filter(code=self.MISSING_CODE).exists())

    def test_track_gidd_raises_permission_denied_not_attribute_error(self):
        with self.assertRaises(PermissionDenied) as caught:
            track_gidd(self.MISSING_CODE, ExternalApiDump.ExternalApiType.GIDD_COUNTRY_REST)
        self.assertEqual(str(caught.exception.detail), "Client is not registered.")

    def test_every_external_endpoint_answers_403_rather_than_raising(self):
        for endpoint in EXTERNAL_API_URLS:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(f"{endpoint}?client_id={self.MISSING_CODE}")
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.content)

    def test_a_live_client_row_is_still_accepted(self):
        # Counter-case: without it an unconditional `raise PermissionDenied` would pass too.
        self.assertEqual(track_gidd(self.LIVE_CODE, ExternalApiDump.ExternalApiType.GIDD_COUNTRY_REST), self.live_client)

    def test_a_deactivated_client_is_still_told_apart_from_a_missing_one(self):
        # Counter-case: the missing-row guard must not shadow the is_active check.
        with self.assertRaises(PermissionDenied) as caught:
            track_gidd(self.INACTIVE_CODE, ExternalApiDump.ExternalApiType.GIDD_COUNTRY_REST)
        self.assertEqual(str(caught.exception.detail), "Client is deactivated.")


class TestIduReferencesDump(HelixAPITestCase):
    def setUp(self):
        super().setUp()
        # share_source=True on purpose: the references dump is generated only with
        # include_sources=False, so a view that keyed the lookup on this flag -- as the shared
        # mixin does for the IDU dumps, which exist in both variants -- would 404 here.
        self.client1 = ClientFactory.create(code="random-code-1", is_active=True, share_source=True)
        # Named values throughout: the dump is a lookup table, so the ids have to come back
        # attached to the right labels, not merely be present.
        self.geo_group = GeographicalGroupFactory.create(name="South Asia")
        self.disaster_type = DisasterTypeFactory.create(name="Earthquake")
        self.disaster_sub_type = DisasterSubTypeFactory.create(type=self.disaster_type, name="Ground shaking")
        self.violence = ViolenceFactory.create(name="Other situations of violence")
        self.violence_sub_type = ViolenceSubTypeFactory.create(violence=self.violence, name="Crime related")
        self.country = CountryFactory.create(
            geographical_group=self.geo_group,
            iso3="AFG",
            idmc_short_name="Afghanistan",
        )

    def _endpoint(self):
        return f"{IDU_REFERENCES_URL}?client_id={self.client1.code}"

    def test_returns_404_when_not_generated(self):
        self.assertEqual(ExternalApiDump.objects.count(), 0)
        response = self.client.get(self._endpoint())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_returns_redirect_after_generation(self):
        generate_idu_options_dump_file()
        response = self.client.get(self._endpoint())
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_returns_202_when_pending_without_file(self):
        generate_idu_options_dump_file()
        ExternalApiDump.objects.filter(
            api_type=ExternalApiDump.ExternalApiType.IDU_REFERENCES,
        ).update(status=ExternalApiDump.Status.PENDING, dump_file=None)
        response = self.client.get(self._endpoint())
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_dump_content_structure(self):
        generate_idu_options_dump_file()
        dump = ExternalApiDump.objects.get(api_type=ExternalApiDump.ExternalApiType.IDU_REFERENCES)
        self.assertEqual(dump.status, ExternalApiDump.Status.COMPLETED)

        with dump.dump_file.open("r") as f:
            data = json.load(f)

        self.assertIn("disaster_types", data)
        self.assertIn("disaster_sub_types", data)
        self.assertIn("violence_types", data)
        self.assertIn("violence_sub_types", data)
        self.assertIn("geographical_groups", data)
        self.assertIn("countries", data)

        # Verify disaster type/subtype shape and linkage
        d_type = next(d for d in data["disaster_types"] if d["id"] == self.disaster_type.id)
        self.assertEqual(d_type["name"], self.disaster_type.name)

        d_sub = next(d for d in data["disaster_sub_types"] if d["id"] == self.disaster_sub_type.id)
        self.assertEqual(d_sub["name"], self.disaster_sub_type.name)
        self.assertEqual(d_sub["type_id"], self.disaster_type.id)

        # Verify violence type/subtype shape and linkage
        v_type = next(v for v in data["violence_types"] if v["id"] == self.violence.id)
        self.assertEqual(v_type["name"], self.violence.name)

        v_sub = next(v for v in data["violence_sub_types"] if v["id"] == self.violence_sub_type.id)
        self.assertEqual(v_sub["name"], self.violence_sub_type.name)
        self.assertEqual(v_sub["type_id"], self.violence.id)

        # Verify country shape
        country = next(c for c in data["countries"] if c["id"] == self.country.id)
        self.assertEqual(country["iso3"], self.country.iso3)
        self.assertEqual(country["idmc_short_name"], self.country.idmc_short_name)
        self.assertEqual(country["geographical_group_id"], self.geo_group.id)
        self.assertIn("bbox", country)
