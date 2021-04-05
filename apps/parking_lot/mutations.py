import graphene
from django.utils.translation import gettext

from apps.parking_lot.models import ParkedItem
from apps.parking_lot.schema import ParkedItemType
from apps.parking_lot.serializers import ParkedItemSerializer, ParkedItemUpdateSerializer
from utils.mutation import generate_input_type_for_serializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker


ParkedItemCreateInputType = generate_input_type_for_serializer(
    'ParkedItemCreateInputType',
    ParkedItemSerializer
)

ParkedItemUpdateInputType = generate_input_type_for_serializer(
    'ParkedItemUpdateInputType',
    ParkedItemUpdateSerializer
)


class CreateParkedItem(graphene.Mutation):
    class Arguments:
        data = ParkedItemCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ParkedItemType)

    @staticmethod
    @permission_checker(['parking_lot.add_parkeditem'])
    def mutate(root, info, data):
        serializer = ParkedItemSerializer(data=data, context=dict(request=info.context.request))
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
                                          context=dict(request=info.context.request))
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
