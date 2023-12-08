import bleach
import django
from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import get_storage_class, default_storage
from django.db.models import FileField, TextField
from django.db.models.fields.files import FieldFile
from html import unescape

from helix.storages import FileSystemMediaStorage

StorageClass = get_storage_class()


def generate_full_media_url(path, absolute=False):
    if not path:
        return ''
    url = default_storage.url(str(path))
    if StorageClass == FileSystemMediaStorage:
        if absolute:
            return f'{settings.BACKEND_BASE_URL}{url}'
    return url


class CachedFieldFile(FieldFile):
    CACHE_KEY = 'url_cache_{}'

    @property
    def url(self):
        if (
            settings.DEFAULT_FILE_STORAGE != 'storages.backends.s3boto3.S3Boto3Storage' or
            getattr(settings, 'AWS_QUERYSTRING_AUTH', False) is False
        ):
            return super().url
        key = self.CACHE_KEY.format(hash(self.name))
        url = cache.get(key)
        if url:
            return url
        url = super().url
        cache.set(key, url, getattr(settings, 'AWS_QUERYSTRING_EXPIRE', 3600))
        return url


class CachedFileField(FileField):
    attr_class = CachedFieldFile


class BleachedTextField(TextField):
    def get_db_prep_value(self, *args, **kwargs):
        value = super(TextField, self).get_db_prep_value(*args, **kwargs)
        if isinstance(value, str):
            return unescape(bleach.clean(value, strip=True))
        return value


django.db.models.TextField.get_db_prep_value = BleachedTextField.get_db_prep_value
