import graphene
from django.utils.translation import gettext, gettext_lazy as _

from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.crisis.models import Crisis
from apps.crisis.schema import CrisisType
from apps.crisis.serializers import CrisisSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker


class CrisisCreateInputType(graphene.InputObjectType):
    """
    Crisis Create InputType
    """
    name = graphene.String(required=True)
    crisis_type = graphene.NonNull(CrisisTypeGrapheneEnum)
    crisis_narrative = graphene.String()
    countries = graphene.List(graphene.NonNull(graphene.ID), required=True)


class CrisisUpdateInputType(graphene.InputObjectType):
    """
    Crisis Update InputType
    """
    id = graphene.ID(required=True)
    name = graphene.String()
    crisis_type = graphene.Field(CrisisTypeGrapheneEnum)
    crisis_narrative = graphene.String()
    countries = graphene.List(graphene.NonNull(graphene.ID))


class CreateCrisis(graphene.Mutation):
    class Arguments:
        data = CrisisCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(CrisisType)

    @staticmethod
    @permission_checker(['crisis.add_crisis'])
    def mutate(root, info, data):
        serializer = CrisisSerializer(data=data)
        if errors := mutation_is_not_valid(serializer):
            return CreateCrisis(errors=errors, ok=False)
        instance = serializer.save()
        return CreateCrisis(result=instance, errors=None, ok=True)


class UpdateCrisis(graphene.Mutation):
    class Arguments:
        data = CrisisUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(CrisisType)

    @staticmethod
    @permission_checker(['crisis.change_crisis'])
    def mutate(root, info, data):
        try:
            instance = Crisis.objects.get(id=data['id'])
        except Crisis.DoesNotExist:
            return UpdateCrisis(errors=[
                CustomErrorType(field='non_field_errors', messages=gettext('Crisis does not exist.'))
            ])
        serializer = CrisisSerializer(instance=instance, data=data, partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateCrisis(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateCrisis(result=instance, errors=None, ok=True)


class DeleteCrisis(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(CrisisType)

    @staticmethod
    @permission_checker(['crisis.delete_crisis'])
    def mutate(root, info, id):
        try:
            instance = Crisis.objects.get(id=id)
        except Crisis.DoesNotExist:
            return DeleteCrisis(errors=[
                CustomErrorType(field='non_field_errors', messages=gettext('Crisis does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteCrisis(result=instance, errors=None, ok=True)


class Mutation(object):
    create_crisis = CreateCrisis.Field()
    update_crisis = UpdateCrisis.Field()
    delete_crisis = DeleteCrisis.Field()
