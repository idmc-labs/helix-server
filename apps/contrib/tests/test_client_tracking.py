import json
from datetime import timedelta

from rest_framework import status

from apps.contrib.models import ClientTrackInfo
from apps.contrib.tasks import (
    generate_idu_options_dump_file,
    generate_idus_all_disaster_dump_file,
    generate_idus_all_dump_file,
    generate_idus_dump_file,
    save_and_delete_tracked_data_from_redis_to_db,
)
from apps.entry.models import ExternalApiDump
from helix.caches import external_api_cache
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


class TestIduReferencesDump(HelixAPITestCase):
    def setUp(self):
        super().setUp()
        self.client1 = ClientFactory.create(code="random-code-1", is_active=True, share_source=True)
        geo_group = GeographicalGroupFactory.create()
        self.disaster_type = DisasterTypeFactory.create()
        self.disaster_sub_type = DisasterSubTypeFactory.create(type=self.disaster_type)
        self.violence = ViolenceFactory.create()
        self.violence_sub_type = ViolenceSubTypeFactory.create(violence=self.violence)
        self.country = CountryFactory.create(geographical_group=geo_group)

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

        self.assertIn("disasterTypes", data)
        self.assertIn("disasterSubTypes", data)
        self.assertIn("violenceTypes", data)
        self.assertIn("violenceSubTypes", data)
        self.assertIn("geographicalGroups", data)
        self.assertIn("countries", data)

        # Verify disaster type/subtype shape and linkage
        d_type = next(d for d in data["disasterTypes"] if d["id"] == self.disaster_type.id)
        self.assertIn("id", d_type)
        self.assertIn("name", d_type)

        d_sub = next(d for d in data["disasterSubTypes"] if d["id"] == self.disaster_sub_type.id)
        self.assertIn("id", d_sub)
        self.assertIn("name", d_sub)
        self.assertEqual(d_sub["type_id"], self.disaster_type.id)

        # Verify violence type/subtype shape and linkage
        v_type = next(v for v in data["violenceTypes"] if v["id"] == self.violence.id)
        self.assertIn("id", v_type)
        self.assertIn("name", v_type)

        v_sub = next(v for v in data["violenceSubTypes"] if v["id"] == self.violence_sub_type.id)
        self.assertIn("id", v_sub)
        self.assertIn("name", v_sub)
        self.assertEqual(v_sub["type_id"], self.violence.id)

        # Verify country shape
        country = next(c for c in data["countries"] if c["id"] == self.country.id)
        self.assertIn("id", country)
        self.assertIn("idmcShortName", country)
        self.assertIn("iso3", country)
        self.assertIn("bbox", country)
        self.assertIn("geographical_group_id", country)
