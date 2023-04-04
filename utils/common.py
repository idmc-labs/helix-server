import datetime
import re
import decimal
from django.core.files.storage import get_storage_class
from django.conf import settings
import tempfile
import logging
from helix import redis
from datetime import timedelta


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


def generate_storage_url_from_path(file_path):
    # instance of the current storage class
    media_storage = get_storage_class()()
    return media_storage.url(file_path)


def get_string_from_list(list_of_string):
    return '; '.join(filter(None, list_of_string))


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
