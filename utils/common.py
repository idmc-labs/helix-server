import datetime
import typing
import functools
import re
import decimal
import tempfile
import logging
from datetime import timedelta

from django.conf import settings
from rest_framework.exceptions import PermissionDenied
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets

from helix import redis
from helix.caches import external_api_cache
from apps.contrib.redis_client_track import track_client
from apps.common.utils import EXTERNAL_ARRAY_SEPARATOR


logger = logging.getLogger(__name__)


def convert_date_object_to_string_in_dict(dictionary):
    """
    Change date objects to string
    """
    for key, value in dictionary.items():
        if isinstance(value, (datetime.date, datetime.datetime)):
            dictionary[key] = str(value)
    return dictionary


def add_clone_prefix(sentence):
    """
    Add prefix in cloned objects
    """
    match = re.match(r"Clone\s*(\d+):\s+(.*)", sentence)
    if match:
        return f"Clone {int(match.group(1)) + 1}: {match.group(2)}"

    match = re.match(r"Clone\s*:\s+(.*)", sentence)
    if match:
        return f"Clone 2: {match.group(1)}"

    return f"Clone: {sentence}"


def is_grid_or_myu_report(start_date, end_date):

    def is_last_day_of_year(date):
        if not date:
            return False
        return date.month == 12 and date.day == 31

    def is_first_day_of_year(date):
        if not date:
            return False
        return date.month == 1 and date.day == 1

    def is_year_equal(start_date, end_date):
        if not start_date:
            return False
        if not end_date:
            return False
        return start_date.year == end_date.year

    def is_last_day_of_sixth_month_in_year(date):
        if not date:
            return False
        return date.month == 6 and date.day == 30

    is_grid_report = (is_first_day_of_year(
        start_date) and is_last_day_of_year(end_date) and is_year_equal(start_date, end_date)
    )
    is_ymu_report = (
        is_first_day_of_year(start_date) and is_last_day_of_sixth_month_in_year(end_date) and
        is_year_equal(start_date, end_date)
    )
    return is_ymu_report or is_grid_report


def get_string_from_list(list_of_string):
    return EXTERNAL_ARRAY_SEPARATOR.join(filter(None, list_of_string))


def get_temp_file(dir=settings.TEMP_FILE_DIRECTORY, **kwargs):
    return tempfile.NamedTemporaryFile(dir=dir, **kwargs)


def get_redis_lock_ttl(lock):
    try:
        return timedelta(seconds=redis.get_connection().ttl(lock.name))
    except Exception:
        pass


def redis_lock(lock_key, timeout=60 * 60 * 4):
    """
    Default Lock lifetime 4 hours
    """
    def _dec(func):
        def _caller(*args, **kwargs):
            key = lock_key.format(*args, **kwargs)
            lock = redis.get_lock(key, timeout)
            have_lock = lock.acquire(blocking=False)
            if not have_lock:
                logger.warning(f'Unable to get lock for {key}(ttl: {get_redis_lock_ttl(lock)})')
                return False
            try:
                return_value = func(*args, **kwargs) or True
            except Exception:
                logger.error('{}.{}'.format(func.__module__, func.__name__), exc_info=True)
                return_value = False
            lock.release()
            return return_value
        _caller.__name__ = func.__name__
        _caller.__module__ = func.__module__
        return _caller
    return _dec


def round_half_up(float_value):
    """
    Returns rounded half upper value, eg 2.5 rounds to 3.0
    """
    return float(
        decimal.Decimal(float_value).quantize(
            0,
            rounding=decimal.ROUND_HALF_UP
        )
    )


def round_and_remove_zero(num):
    if num is None or num == 0:
        return None
    absolute_num = abs(num)
    sign = 1 if num > 0 else -1
    if absolute_num <= 100:
        return sign * absolute_num
    if absolute_num <= 1000:
        return sign * round(absolute_num / 10) * 10
    if absolute_num < 10000:
        return sign * round(absolute_num / 100) * 100
    return sign * round(num / 1000) * 1000


def track_gidd(client_id, endpoint_type, viewset: viewsets.GenericViewSet = None):
    from apps.contrib.models import Client

    if viewset and getattr(viewset, "swagger_fake_view", False):
        # Skip check for swagger view
        return

    if client_id not in external_api_cache.get('client_ids', []):
        raise PermissionDenied('Client is not registered.')

    client = Client.objects.filter(code=client_id).first()
    if not client.is_active:
        raise PermissionDenied('Client is deactivated.')

    # Track client
    track_client(
        endpoint_type,
        client_id,
    )


class RuntimeProfile:
    label: str
    start: typing.Optional[datetime.datetime]

    def __init__(self, label: str = 'N/A'):
        self.label = label
        self.start = None

    def __call__(self, func):
        self.label = func.__name__

        @functools.wraps(func)
        def decorated(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return decorated

    def __enter__(self):
        self.start = datetime.datetime.now()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        assert self.start is not None
        time_delta = datetime.datetime.now() - self.start
        logger.info(f'Runtime with <{self.label}>: {time_delta}')


client_id = extend_schema(
    parameters=[
        OpenApiParameter(
            "client_id",
            OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
        )
    ],
)
