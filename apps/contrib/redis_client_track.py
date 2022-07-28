from django.core.cache import caches
from django.utils import timezone

external_api_cache = caches['external_api']


def get_external_redis_data(key):
    return external_api_cache.get(key)


def create_client_track_cache_key(api_type, client_id):
    date_today = timezone.now().strftime('%Y-%m-%d')
    return f'trackinfo:{date_today}:{api_type}:{client_id}'


def get_client_tracked_cache_keys():
    return external_api_cache.keys('trackinfo:*')


def delete_external_redis_record_by_key(key):
    return external_api_cache.delete(key)


def track_client(api_type, client_id):
    cache_key = create_client_track_cache_key(api_type, client_id)
    try:
        external_api_cache.incr(cache_key)
    except ValueError:
        external_api_cache.set(cache_key, 1, None)


def set_client_ids_in_redis(client_ids):
    external_api_cache.set('client_ids', client_ids, None)
    return True
