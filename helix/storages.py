import threading

from django.conf import settings
from django.core.files.storage import FileSystemStorage, Storage, get_storage_class
from storages.backends.s3boto3 import S3Boto3Storage

_storage_auth_lock = threading.Lock()


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
    default_acl = "public-read"
    location = settings.STATIC_ROOT

    def get_default_settings(self):
        return {
            **super().get_default_settings(),
            "bucket_name": settings.AWS_STORAGE_STATIC_BUCKET_NAME,
        }


class S3MediaStorage(S3Boto3Storage):
    location = settings.MEDIA_ROOT

    def get_default_settings(self):
        return {
            **super().get_default_settings(),
            "bucket_name": settings.AWS_STORAGE_MEDIA_BUCKET_NAME,
        }


class S3ExternalMediaStorage(S3Boto3Storage):
    default_acl = "public-read"
    location = settings.EXTERNAL_MEDIA_ROOT

    def get_default_settings(self):
        return {
            **super().get_default_settings(),
            "bucket_name": settings.AWS_STORAGE_EXTERNAL_BUCKET_NAME,
        }


def get_external_storage() -> Storage:
    storage_class = get_storage_class(import_path=settings.EXTERNAL_FILE_STORAGE)
    return storage_class()


# FIXME: Check if thread lock is enough?? or it breaks
class TemporaryStorageEnableAuthString:
    """Temporarily enable querystring auth to generate signed URLs with response override parameters."""

    def __init__(self, storage: S3Boto3Storage):
        self._storage = storage

    def __enter__(self):
        _storage_auth_lock.acquire()
        if isinstance(self._storage, S3Boto3Storage):
            self._original = self._storage.querystring_auth
            self._storage.querystring_auth = True

    def __exit__(self, exc_type, exc_value, exc_tb):
        if isinstance(self._storage, S3Boto3Storage):
            self._storage.querystring_auth = self._original
        _storage_auth_lock.release()
