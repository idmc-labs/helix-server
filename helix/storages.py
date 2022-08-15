from storages.backends.s3boto3 import S3Boto3Storage
from django.utils.functional import LazyObject
from django.core.files.storage import FileSystemStorage, get_storage_class
from django.conf import settings


# File System Storage
class FileSystemStaticStorage(FileSystemStorage):
    location = settings.STATIC_ROOT
    base_url = settings.STATIC_URL


class FileSystemMediaStorage(FileSystemStorage):
    location = settings.MEDIA_ROOT
    base_url = settings.MEDIA_URL


class FileSystemExternalMediaStorage(FileSystemStorage):
    location = settings.EXTERNAL_MEDIA_ROOT
    base_url = settings.EXTERNAL_MEDIA_URL


# S3
class S3StaticStorage(S3Boto3Storage):
    default_acl = 'public-read'
    location = settings.STATIC_ROOT

    def get_default_settings(self):
        return {
            **super().get_default_settings(),
            'bucket_name': settings.AWS_STORAGE_STATIC_BUCKET_NAME,
        }


class S3MediaStorage(S3Boto3Storage):
    location = settings.MEDIA_ROOT

    def get_default_settings(self):
        return {
            **super().get_default_settings(),
            'bucket_name': settings.AWS_STORAGE_MEDIA_BUCKET_NAME,
        }


class S3ExternalMediaStorage(S3Boto3Storage):
    default_acl = 'public-read'
    location = settings.EXTERNAL_MEDIA_ROOT

    def get_default_settings(self):
        return {
            **super().get_default_settings(),
            'bucket_name': settings.AWS_STORAGE_EXTERNAL_BUCKET_NAME,
        }


def get_external_storage_class():
    return get_storage_class(import_path=settings.EXTERNAL_FILE_STORAGE)


class ExternalStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_external_storage_class()()


external_storage = ExternalStorage()
