from django.conf import settings
from django.core.cache import cache
from django.db.models import FileField
from django.db.models.fields.files import FieldFile


class CachedFieldFile(FieldFile):
    CACHE_KEY = 'url_cache_{}'

    @property
    def url(self):
        if settings.DEFAULT_FILE_STORAGE != 'storages.backends.s3boto3.S3Boto3Storage':
            return super().url
        key = self.CACHE_KEY.format(hash(self.name))
        url = cache.get(key)
        if url:
            return url
        url = super().url
        cache.set(key, url, settings.AWS_QUERYSTRING_EXPIRE)
        return url


class CachedFileField(FileField):
    attr_class = CachedFieldFile
