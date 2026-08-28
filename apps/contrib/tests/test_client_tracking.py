from datetime import timedelta

from rest_framework import status
from rest_framework.exceptions import PermissionDenied

from apps.contrib.models import Client, ClientTrackInfo
from apps.contrib.tasks import (
    generate_idus_all_disaster_dump_file,
    generate_idus_all_dump_file,
    generate_idus_dump_file,
    save_and_delete_tracked_data_from_redis_to_db,
)
from apps.entry.models import ExternalApiDump
from helix.caches import external_api_cache
from utils.common import track_gidd
from utils.factories import ClientFactory
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

EXTERNAL_API_URLS = [*IDU_EXPORT_URLS, *GIDD_API_URLS]


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
