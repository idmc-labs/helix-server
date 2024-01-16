import logging
from operator import itemgetter
from datetime import datetime

from django.utils import timezone

from helix.caches import external_api_cache
from apps.common.utils import REDIS_SEPARATOR


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_external_redis_data(key):
    return external_api_cache.get(key)


def create_client_track_cache_key(api_type, client_id):
    date_today = timezone.now().strftime('%Y-%m-%d')
    return REDIS_SEPARATOR.join(['trackinfo', date_today, api_type, client_id])


def get_client_tracked_cache_keys():
    return external_api_cache.keys(f'trackinfo{REDIS_SEPARATOR}*')


def delete_external_redis_record_by_key(*keys):
    return [
        external_api_cache.delete(key)
        for key in keys
    ]


def track_client(api_type, client_id):
    cache_key = create_client_track_cache_key(api_type, client_id)
    try:
        external_api_cache.incr(cache_key)
    except ValueError:
        external_api_cache.set(cache_key, 1, None)


def set_client_ids_in_redis(client_ids):
    external_api_cache.set('client_ids', client_ids, None)
    return True


def pull_track_data_from_redis(tracking_keys):
    from apps.contrib.models import Client

    client_mapping = {
        code: _id
        for _id, code in Client.objects.values_list('id', 'code')
    }
    tracked_data_from_redis = {}

    for key in tracking_keys:
        tracked_date, api_type, code = itemgetter(1, 2, 3)(key.split(REDIS_SEPARATOR))
        tracked_date = datetime.strptime(tracked_date, "%Y-%m-%d").date()
        requests_per_day = get_external_redis_data(key)

        # Only save records before today
        if tracked_date >= datetime.now().date():
            continue

        client_id = client_mapping.get(code)
        if client_id is None:
            logger.error(f'Client with is code {code} does not exist.')
            continue

        tracked_data_from_redis[key] = dict(
            api_type=api_type,
            client_id=client_id,
            tracked_date=tracked_date,
            requests_per_day=requests_per_day,
        )
    return tracked_data_from_redis
