from rest_framework import status
from datetime import timedelta
from utils.tests import HelixAPITestCase
from utils.factories import ClientFactory

from apps.entry.models import ExternalApiDump
from apps.contrib.models import ClientTrackInfo
from apps.contrib.tasks import (
    generate_idus_dump_file,
    generate_idus_all_dump_file,
    generate_idus_all_disaster_dump_file,
    save_and_delete_tracked_data_from_redis_to_db,
)
from helix.caches import external_api_cache


class TestExternalClientTrack(HelixAPITestCase):
    def setUp(self):
        super().setUp()
        self.idus_url = '/external-api/idus'
        self.idus_all_url = '/external-api/idus-all'
        self.idus_all_disaster_url = '/external-api/idus-all-disaster'
        self.client1 = ClientFactory.create(code='random-code-1')
        self.client2 = ClientFactory.create(code='random-code-2')

    def test_should_raise_permission_denied_if_client_is_not_registered(self):
        for endpoint in [self.idus_url, self.idus_all_url]:
            response = self.client.get(self.idus_url)
            assert response.status_code == status.HTTP_403_FORBIDDEN

        # Test with invalid client ids
        endpoints = [
            f'{self.idus_url}?client_id=random-client-id-1',
            f'{self.idus_all_url}?client_id=random-client-id-2',
            f'{self.idus_all_disaster_url}?client_id=random-client-id-2',
        ]

        for endpoint in endpoints:
            response = self.client.get(self.idus_url)
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_should_return_api_data_for_registered_clients(self):

        # Test with invalid client ids
        endpoints = [
            f'{self.idus_url}?client_id={self.client1.code}',
            f'{self.idus_all_url}?client_id={self.client2.code}',
            f'{self.idus_all_disaster_url}?client_id={self.client2.code}',
        ]

        def _response_status_check(status_code):
            for endpoint in endpoints:
                response = self.client.get(endpoint)
                assert response.status_code == status_code

        _response_status_check(status.HTTP_404_NOT_FOUND)

        # Let's trigger dump generator
        generate_idus_dump_file()
        generate_idus_all_dump_file()
        generate_idus_all_disaster_dump_file()

        _response_status_check(status.HTTP_302_FOUND)

        ExternalApiDump.objects.update(
            status=ExternalApiDump.Status.PENDING,
            dump_file=None,
        )
        _response_status_check(status.HTTP_202_ACCEPTED)

    def test_tracked_data(self):
        # Test with invalid client ids
        endpoints = [
            f'{self.idus_url}?client_id={self.client1.code}',
            f'{self.idus_url}?client_id={self.client2.code}',
            f'{self.idus_all_url}?client_id={self.client1.code}',
            f'{self.idus_all_url}?client_id={self.client2.code}',
            f'{self.idus_all_disaster_url}?client_id={self.client1.code}',
            f'{self.idus_all_disaster_url}?client_id={self.client2.code}',
        ]

        # Assume yesterdays data
        self.now_patcher.start().return_value = self.now_datetime - timedelta(days=1)
        for endpoint in endpoints:
            self.client.get(endpoint)

        # Sync redis data to database
        save_and_delete_tracked_data_from_redis_to_db()
        self.assertEqual(ClientTrackInfo.objects.count(), 6)

        # Again track client ids for same date
        for endpoint in endpoints:
            self.client.get(endpoint)

        # Resync redis data for same date
        save_and_delete_tracked_data_from_redis_to_db()
        self.assertEqual(ClientTrackInfo.objects.count(), 6)

        # Again track client ids for same date
        for endpoint in endpoints:
            self.client.get(endpoint)

        # Resync redis data for same date
        save_and_delete_tracked_data_from_redis_to_db()
        self.assertEqual(ClientTrackInfo.objects.count(), 6)

        # For each client track info requests per day should be 1 for each api type
        for obj in ClientTrackInfo.objects.all():
            self.assertEqual(obj.requests_per_day, 3)

    def test_should_update_duplicated_tracking_record(self):
        # Create duplicated redis client tracking keys
        keys = [
            'trackinfo:2022-07-09:idus',
            'trackinfo:2022-07-12:idus',
            'trackinfo:2022-07-28:idus',
            'trackinfo:2022-07-05:idus',
            'trackinfo:2022-07-04:idus',
            'trackinfo:2022-07-01:idus',
            'trackinfo:2022-07-06:idus',
            'trackinfo:2022-08-01:idus',
            'trackinfo:2022-08-02:idus',
            'trackinfo:2022-07-14:idus',
            'trackinfo:2022-07-03:idus',
            'trackinfo:2022-07-13:idus',
            'trackinfo:2022-07-02:idus',
            'trackinfo:2022-07-07:idus',
        ]
        for key in keys:
            external_api_cache.set(f'{key}:{self.client1.code}', 100, None)

        # Trigger task
        save_and_delete_tracked_data_from_redis_to_db()
        self.assertEqual(ClientTrackInfo.objects.count(), 14)

        for key in keys:
            external_api_cache.set(f'{key}:{self.client1.code}', 100, None)

        # Trigger task
        save_and_delete_tracked_data_from_redis_to_db()
        self.assertEqual(ClientTrackInfo.objects.count(), 14)
