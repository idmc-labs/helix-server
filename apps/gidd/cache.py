import hashlib
import json
import os
import typing

import django_filters
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.http import HttpResponse
from django.shortcuts import redirect
from rest_framework import serializers
from rest_framework.request import Request
from storages.backends.s3boto3 import S3Boto3Storage

from helix.storages import TemporaryStorageEnableAuthString, get_external_storage

from .models import ReleaseMetadata, StatusLog

external_storage = get_external_storage()


class GiddExportCache:
    FILE_DESTINATION_PREFIX = "gidd-cache-export"

    class Key(models.TextChoices):
        # {StatusLog.id}/{export-name}/{export-hash}
        DISAGGREGATION_EXPORT = "disaggregation-export"
        DISAGGREGATION_EXPORT_GEOJSON = "disaggregation-export-geojson"
        DISASTER_EXPORT = "disaster-export"
        DISPLACEMENT_EXPORT = "displacement-export"

    @staticmethod
    def last_release_date() -> str:
        return StatusLog.last_release_date(format="%Y-%m-%d-%H-%M-%S") or "NA"

    @classmethod
    def generate_cache_key(cls, key: Key, data: dict, filename: str) -> typing.Tuple[bytes, str]:
        last_release_date = cls.last_release_date()

        hashable = json.dumps(
            data,
            sort_keys=True,
            cls=DjangoJSONEncoder,
        ).encode("utf-8")

        hash_md5 = hashlib.md5()
        hash_md5.update(hashable)
        return hashable, os.path.join(
            cls.FILE_DESTINATION_PREFIX,
            "{}",
            key,
            "{}",
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
    def build_cache_data(
        cls,
        query_params: dict,
        filter_sets: typing.List[django_filters.FilterSet],
    ) -> dict:
        release_meta_data = ReleaseMetadata.objects.last()
        if not release_meta_data:
            raise serializers.ValidationError("Release metadata is not configured.")

        release_year = release_meta_data.release_year
        if (
            query_params.get("release_environment") or ""
        ).lower() == ReleaseMetadata.ReleaseEnvironment.PRE_RELEASE.name.lower():
            release_year = release_meta_data.pre_release_year

        clean_data = {
            k: v
            for k, v in query_params.items()
            if k in [field for filter_set in filter_sets for field in filter_set.get_filters()]
        }
        clean_data.pop("client_id", None)
        clean_data.pop("release_environment", None)
        return {
            **clean_data,
            "release_year": release_year,
            # `ordering` is a filter-backend param, not a filterset field, so it is absent from
            # `clean_data`. Without it two requests differing only in sort share one cached file and
            # the second caller is served the first caller's order.
            "ordering": query_params.get("ordering") or "",
        }

    @classmethod
    def get_or_create(
        cls,
        filename: str,
        request: Request,
        filter_sets: typing.List[django_filters.FilterSet],
        key: Key,
        export_generator: typing.Callable,
        s3_parameters: dict,
    ) -> HttpResponse:
        # When disabled, bypass the cache/storage entirely and stream the
        # generated file directly (the pre-cache behaviour).
        if settings.GIDD_EXPORT_CACHE_DISABLED:
            response = HttpResponse(
                content=export_generator(),
                content_type=s3_parameters["ResponseContentType"],
            )
            response["Content-Disposition"] = s3_parameters["ResponseContentDisposition"]
            return response

        data = cls.build_cache_data(request.query_params, filter_sets)

        cache_key = cls._get_or_create(key, data, filename, export_generator)
        if isinstance(external_storage, S3Boto3Storage):
            with TemporaryStorageEnableAuthString(external_storage):
                return redirect(
                    external_storage.url(
                        cache_key,
                        parameters=s3_parameters,
                    )
                )
        return redirect(request.build_absolute_uri(external_storage.url(cache_key)))
