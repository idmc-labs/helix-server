import graphene
from django.utils.translation import gettext

from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.contextualupdate.models import ContextualUpdate
from apps.contextualupdate.schema import ContextualUpdateType
from apps.contextualupdate.serializers import ContextualUpdateSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker


class ContextualUpdateInputMixin:
    preview = graphene.ID()
    article_title = graphene.String()
    sources = graphene.List(graphene.NonNull(graphene.ID))
    publishers = graphene.List(graphene.NonNull(graphene.ID))
    publish_date = graphene.DateTime()
    source_excerpt = graphene.String()
    idmc_analysis = graphene.String()
    is_confidential = graphene.Boolean()
    tags = graphene.List(graphene.NonNull(graphene.ID))
    countries = graphene.List(graphene.NonNull(graphene.ID))
    crisis_types = graphene.List(graphene.NonNull(CrisisTypeGrapheneEnum))


class ContextualUpdateCreateInputType(ContextualUpdateInputMixin,
                                      graphene.InputObjectType):
    url = graphene.String()
    document = graphene.ID()


class ContextualUpdateUpdateInputType(ContextualUpdateInputMixin,
                                      graphene.InputObjectType):
    id = graphene.ID(required=True)


class CreateContextualUpdate(graphene.Mutation):
    class Arguments:
        data = ContextualUpdateCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ContextualUpdateType)

    @staticmethod
    @permission_checker(['contextualupdate.add_contextualupdate'])
    def mutate(root, info, data):
        serializer = ContextualUpdateSerializer(data=data, context=dict(request=info.context.request))
        if errors := mutation_is_not_valid(serializer):
            return CreateContextualUpdate(errors=errors, ok=False)
        instance = serializer.save()
        return CreateContextualUpdate(result=instance, errors=None, ok=True)


class UpdateContextualUpdate(graphene.Mutation):
    class Arguments:
        data = ContextualUpdateUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ContextualUpdateType)

    @staticmethod
    @permission_checker(['contextualupdate.change_contextualupdate'])
    def mutate(root, info, data):
        try:
            instance = ContextualUpdate.objects.get(id=data['id'])
        except ContextualUpdate.DoesNotExist:
            return UpdateContextualUpdate(errors=[
                dict(field='nonFieldErrors', messages=gettext('Contextual Update does not exist.'))
            ])
        serializer = ContextualUpdateSerializer(instance=instance, data=data, partial=True,
                                                context=dict(request=info.context.request))
        if errors := mutation_is_not_valid(serializer):
            return UpdateContextualUpdate(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateContextualUpdate(result=instance, errors=None, ok=True)


class DeleteContextualUpdate(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ContextualUpdateType)

    @staticmethod
    @permission_checker(['contextualupdate.delete_contextualupdate'])
    def mutate(root, info, id):
        try:
            instance = ContextualUpdate.objects.get(id=id)
        except ContextualUpdate.DoesNotExist:
            return DeleteContextualUpdate(errors=[
                dict(field='nonFieldErrors', messages=gettext('ContextualUpdate does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteContextualUpdate(result=instance, errors=None, ok=True)


class Mutation(object):
    create_contextual_update = CreateContextualUpdate.Field()
    update_contextual_update = UpdateContextualUpdate.Field()
    delete_contextual_update = DeleteContextualUpdate.Field()
