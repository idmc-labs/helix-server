import graphene
from django.db import transaction
from django.utils.translation import gettext

from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.mutation import generate_input_type_for_serializer
from utils.permissions import is_authenticated, permission_checker

from .models import GiddRelease
from .schema import GiddReleaseMetadataType, GiddReleaseType, GiddStatusLogType
from .serializers import (
    GiddReleaseSerializer,
    GiddReleaseUpdateSerializer,
    ReleaseMetadataSerializer,
)
from .tasks import GiddRunRefused, start_gidd_update_run


class GiddUpdateData(graphene.Mutation):
    class Arguments:
        release_id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(GiddStatusLogType)

    @staticmethod
    @is_authenticated()
    @permission_checker(["gidd.update_gidd_data_gidd"])
    def mutate(root, info, release_id):
        try:
            instance = start_gidd_update_run(
                release_id=release_id,
                user=info.context.user,
            )
        except GiddRunRefused as e:
            return GiddUpdateData(
                errors=[dict(field="nonFieldErrors", messages=str(e))],
                ok=False,
            )

        return GiddUpdateData(result=instance, ok=True)


GiddReleaseMetadataInputType = generate_input_type_for_serializer(
    "ReleaseMetadataInputType",
    ReleaseMetadataSerializer,
)


class GiddUpdateReleaseMetaData(graphene.Mutation):
    class Arguments:
        data = GiddReleaseMetadataInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(GiddReleaseMetadataType)

    @staticmethod
    @is_authenticated()
    @permission_checker(["gidd.update_release_meta_data_gidd"])
    def mutate(root, info, data):
        serializer = ReleaseMetadataSerializer(data=data, context={"request": info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return GiddUpdateReleaseMetaData(errors=errors, ok=False)
        instance = serializer.save()
        # No regeneration: the release metadata is a filter applied over already-generated
        # data, and nothing in the generation path reads it. The saved row is the active one
        # immediately, which is why it is edited after a release has been generated and its
        # status log recorded, not before.
        return GiddUpdateReleaseMetaData(result=instance, errors=None, ok=True)


# GIDD Release

GiddReleaseCreateInputType = generate_input_type_for_serializer(
    "GiddReleaseCreateInputType",
    GiddReleaseSerializer,
)

GiddReleaseUpdateInputType = generate_input_type_for_serializer(
    "GiddReleaseUpdateInputType",
    GiddReleaseUpdateSerializer,
)


class CreateGiddRelease(graphene.Mutation):
    class Arguments:
        data = GiddReleaseCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(GiddReleaseType)

    @staticmethod
    @is_authenticated()
    @permission_checker(["gidd.manage_release_gidd"])
    def mutate(root, info, data):
        serializer = GiddReleaseSerializer(data=data, context={"request": info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return CreateGiddRelease(errors=errors, ok=False)
        instance = serializer.save()
        return CreateGiddRelease(result=instance, errors=None, ok=True)


class UpdateGiddRelease(graphene.Mutation):
    class Arguments:
        data = GiddReleaseUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(GiddReleaseType)

    @staticmethod
    @is_authenticated()
    @permission_checker(["gidd.manage_release_gidd"])
    def mutate(root, info, data):
        with transaction.atomic():
            instance = GiddRelease.objects.select_for_update().filter(id=data["id"]).first()
            if instance is None:
                return UpdateGiddRelease(
                    errors=[dict(field="nonFieldErrors", messages=gettext("GIDD release does not exist."))],
                    ok=False,
                )
            if instance.is_edit_window_closed():
                return UpdateGiddRelease(
                    errors=[dict(field="nonFieldErrors", messages=str(GiddRelease.EDIT_WINDOW_CLOSED_MESSAGE))],
                    ok=False,
                )
            serializer = GiddReleaseUpdateSerializer(
                instance=instance,
                data=data,
                partial=True,
                context={"request": info.context.request},
            )
            if errors := mutation_is_not_valid(serializer):
                return UpdateGiddRelease(errors=errors, ok=False)
            instance = serializer.save()
        return UpdateGiddRelease(result=instance, errors=None, ok=True)


class Mutation(object):
    gidd_update_data = GiddUpdateData.Field()
    gidd_update_release_meta_data = GiddUpdateReleaseMetaData.Field()
    create_gidd_release = CreateGiddRelease.Field()
    update_gidd_release = UpdateGiddRelease.Field()
