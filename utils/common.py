import datetime
import re
from django.core.files.storage import get_storage_class
from django.conf import settings
import tempfile
from django.core.cache import caches
from django.utils import timezone

external_api_cache = caches['external_api']


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


def track_client(api_type, client_id):
    date_today = timezone.now().strftime('%Y-%m-%d')
    cache_key = f'trackinfo:{date_today}:{api_type}:{client_id}'
    try:
        external_api_cache.incr(cache_key)
    except ValueError:
        external_api_cache.set(cache_key, 1, None)
