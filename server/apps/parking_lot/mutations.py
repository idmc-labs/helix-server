import graphene
from django.utils.translation import gettext

from apps.parking_lot.models import ParkedItem
from apps.parking_lot.schema import ParkedItemType
from apps.parking_lot.serializers import ParkedItemSerializer
from apps.parking_lot.enums import ParkedItemGrapheneEnum
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker


class ParkedItemCreateInputType(graphene.InputObjectType):
    country = graphene.ID(required=True)
    title = graphene.String(required=True)
    url = graphene.String(required=True)
    assigned_to = graphene.ID(required=False)
    status = graphene.NonNull(ParkedItemGrapheneEnum)
    comments = graphene.String(required=False)


class ParkedItemUpdateInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    country = graphene.ID()
    title = graphene.String()
    url = graphene.String()
    assigned_to = graphene.ID()
    status = graphene.Field(ParkedItemGrapheneEnum)
    comments = graphene.String()


class CreateParkedItem(graphene.Mutation):
    class Arguments:
        data = ParkedItemCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ParkedItemType)

    @staticmethod
    @permission_checker(['parking_lot.add_parkeditem'])
    def mutate(root, info, data):
        serializer = ParkedItemSerializer(data=data, context=dict(request=info.context))
        if errors := mutation_is_not_valid(serializer):
            return CreateParkedItem(errors=errors, ok=False)
        instance = serializer.save()
        return CreateParkedItem(result=instance, errors=None, ok=True)


class UpdateParkedItem(graphene.Mutation):
    class Arguments:
        data = ParkedItemUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ParkedItemType)

    @staticmethod
    @permission_checker(['parking_lot.change_parkeditem'])
    def mutate(root, info, data):
        try:
            instance = ParkedItem.objects.get(id=data['id'], created_by=info.context.user)
        except ParkedItem.DoesNotExist:
            return UpdateParkedItem(errors=[
                dict(field='nonFieldErrors', messages=gettext('Parked item does not exist.'))
            ])
        serializer = ParkedItemSerializer(instance=instance, data=data, partial=True,
                                          context=dict(request=info.context))
        if errors := mutation_is_not_valid(serializer):
            return UpdateParkedItem(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateParkedItem(result=instance, errors=None, ok=True)


class DeleteParkedItem(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ParkedItemType)

    @staticmethod
    @permission_checker(['parking_lot.delete_parkeditem'])
    def mutate(root, info, id):
        try:
            instance = ParkedItem.objects.get(id=id, created_by=info.context.user)
        except ParkedItem.DoesNotExist:
            return DeleteParkedItem(errors=[
                dict(field='nonFieldErrors', messages=gettext('Parked item does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteParkedItem(result=instance, errors=None, ok=True)


class Mutation(object):
    create_parked_item = CreateParkedItem.Field()
    update_parked_item = UpdateParkedItem.Field()
    delete_parked_item = DeleteParkedItem.Field()
