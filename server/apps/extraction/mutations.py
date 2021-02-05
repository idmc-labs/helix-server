from django.utils.translation import gettext
import graphene

from apps.extraction.models import ExtractionQuery
from apps.extraction.serializers import ExtractionQuerySerializer
from apps.extraction.schema import (
    ExtractionQueryObjectType,
)
from apps.entry.enums import RoleGrapheneEnum
from utils.error_types import CustomErrorType, mutation_is_not_valid


class CommonExtractionInputMixin:
    event_regions = graphene.List(graphene.NonNull(graphene.ID), required=False)
    event_countries = graphene.List(graphene.NonNull(graphene.ID), required=False)
    event_crises = graphene.List(graphene.NonNull(graphene.ID), required=False)
    figure_categories = graphene.List(graphene.NonNull(graphene.ID), required=False)
    figure_start_after = graphene.Date(required=False)
    figure_end_before = graphene.Date(required=False)
    figure_roles = graphene.List(graphene.NonNull(RoleGrapheneEnum), required=False)
    event_tags = graphene.List(graphene.NonNull(graphene.ID), required=False)
    event_article_title = graphene.String()


class CreateExtractInputType(CommonExtractionInputMixin, graphene.InputObjectType):
    name = graphene.String(required=True)


class UpdateExtractInputType(CommonExtractionInputMixin, graphene.InputObjectType):
    name = graphene.String()
    id = graphene.ID(required=True)


class CreateExtraction(graphene.Mutation):
    class Arguments:
        data = CreateExtractInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ExtractionQueryObjectType)

    @staticmethod
    def mutate(root, info, data):  # noqa
        serializer = ExtractionQuerySerializer(data=data,
                                               context={'request': info.context})
        if errors := mutation_is_not_valid(serializer):  # noqa
            return CreateExtraction(errors=errors, ok=False)
        instance = serializer.save()
        return CreateExtraction(result=instance, errors=None, ok=True)


class UpdateExtraction(graphene.Mutation):
    class Arguments:
        data = UpdateExtractInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ExtractionQueryObjectType)

    @staticmethod
    def mutate(root, info, data):  # noqa
        try:
            instance = ExtractionQuery.objects.get(id=data['id'],
                                                   created_by=info.context.user)  # TODO: correct?
        except ExtractionQuery.DoesNotExist:
            return UpdateExtraction(errors=[
                dict(field='nonFieldErrors', messages=gettext('Extraction query does not exist.'))
            ])
        serializer = ExtractionQuerySerializer(instance=instance,
                                               data=data,
                                               context={'request': info.context})
        if errors := mutation_is_not_valid(serializer):  # noqa
            return CreateExtraction(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateExtraction(result=instance, errors=None, ok=True)


class DeleteExtraction(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ExtractionQueryObjectType)

    @staticmethod
    def mutate(root, info, id):
        try:
            instance = ExtractionQuery.objects.get(id=id,
                                                   created_by=info.context.user)  # TODO: correct?
        except ExtractionQuery.DoesNotExist:
            return DeleteExtraction(errors=[
                dict(field='nonFieldErrors', messages=gettext('Extraction Query does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteExtraction(result=instance, errors=None, ok=True)


class Mutation:
    create_extraction = CreateExtraction.Field()
    update_extraction = UpdateExtraction.Field()
    delete_extraction = DeleteExtraction.Field()
