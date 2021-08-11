import bleach
import django
from django.conf import settings
from django.core.cache import cache
from django.db.models import FileField, TextField
from django.db.models.fields.files import FieldFile
from html import unescape
from django.utils.html import strip_tags


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
        value = super().get_db_prep_value(*args, **kwargs)
        if isinstance(value, str):
            return unescape(bleach.clean(strip_tags(value)))
        return value


django.db.models.TextField = BleachedTextField
