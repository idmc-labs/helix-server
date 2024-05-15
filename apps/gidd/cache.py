import typing
import hashlib
import os
import json
import django_filters
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.core.files.base import ContentFile
from rest_framework.request import Request
from storages.backends.s3boto3 import S3Boto3Storage

from helix.storages import get_external_storage

from .models import StatusLog, ReleaseMetadata

external_storage = get_external_storage()


class ExternalStorageEnableAuthString:
    initial_value = getattr(external_storage, 'querystring_auth', None)

    def __enter__(self):
        if isinstance(external_storage, S3Boto3Storage):
            external_storage.querystring_auth = True

    def __exit__(self, exc_type, exc_value, exc_tb):
        if isinstance(external_storage, S3Boto3Storage):
            external_storage.querystring_auth = self.initial_value


class GiddExportCache:

    FILE_DESTINATION_PREFIX = 'gidd-cache-export'

    class Key(models.TextChoices):
        # {StatusLog.id}/{export-name}/{export-hash}
        DISAGGREGATION_EXPORT = 'disaggregation-export'
        DISAGGREGATION_EXPORT_GEOJSON = 'disaggregation-export-geojson'
        DISASTER_EXPORT = 'disaster-export'
        DISPLACEMENT_EXPORT = 'displacement-export'

    @staticmethod
    def last_release_date() -> str:
        return StatusLog.last_release_date(strf_format='%Y-%m-%d-%H-%M-%S') or 'NA'

    @classmethod
    def generate_cache_key(cls, key: Key, data: dict, filename: str) -> typing.Tuple[bytes, str]:
        last_release_date = cls.last_release_date()

        hashable = json.dumps(
            data,
            sort_keys=True,
            cls=DjangoJSONEncoder,
        ).encode('utf-8')

        hash_md5 = hashlib.md5()
        hash_md5.update(hashable)
        return hashable, os.path.join(
            cls.FILE_DESTINATION_PREFIX,
            '{}',
            key,
            '{}',
            filename,
        ).format(last_release_date, hash_md5.hexdigest())

    @classmethod
    def _get_or_create(
        cls,
        key: Key,
        data: dict,
        filename: str,
        export_generator: typing.Callable,
    ) -> str:
        key_data, cache_key = cls.generate_cache_key(key, data, filename)
        if external_storage.exists(cache_key):
            return cache_key
        # Save file as well
        external_storage.save(cache_key, ContentFile(export_generator()))
        # Save metadata as well
        external_storage.save(f"{cache_key}.json", ContentFile(key_data))
        return cache_key

    @classmethod
    def get_or_create(
        cls,
        filename: str,
        request: Request,
        filter_sets: typing.List[django_filters.FilterSet],
        key: Key,
        export_generator: typing.Callable,
        s3_parameters: dict,
    ) -> str:
        release_meta_data = ReleaseMetadata.objects.last()
        if not release_meta_data:
            # TODO:
            raise Exception('Release metadata is not configured.')

        release_year = release_meta_data.release_year
        if (
            request.query_params.get('release_environment').lower() ==
            ReleaseMetadata.ReleaseEnvironment.PRE_RELEASE.name.lower()
        ):
            release_year = release_meta_data.pre_release_year

        # Only look at fields used by filter_set
        clean_data = {
            k: v
            for k, v in request.query_params.items()
            if k in [
                field
                for filter_set in filter_sets
                for field in filter_set.get_filters()
            ]
        }
        # Remove client_id is exists
        clean_data.pop('cliend_id', None)
        # release_environment is replaced by release_year
        clean_data.pop('release_environment', None)
        data = {
            **clean_data,
            'release_year': release_year,
        }

        cache_key = cls._get_or_create(key, data, filename, export_generator)
        if isinstance(external_storage, S3Boto3Storage):
            with ExternalStorageEnableAuthString():
                return external_storage.url(
                    cache_key,
                    parameters=s3_parameters,
                )
        return request.build_absolute_uri(
            external_storage.url(cache_key)
        )
