import graphene
from django.utils.translation import gettext

from apps.parking_lot.models import ParkedItem
from apps.parking_lot.schema import ParkedItemType
from apps.parking_lot.serializers import ParkedItemSerializer, ParkedItemUpdateSerializer
from apps.parking_lot.filters import ParkingLotFilter
from apps.contrib.serializers import ExcelDownloadSerializer
from utils.mutation import generate_input_type_for_serializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker
from utils.common import convert_date_object_to_string_in_dict
from utils.filters import (
    generate_type_for_filter_set,
)


ParkedItemCreateInputType = generate_input_type_for_serializer(
    'ParkedItemCreateInputType',
    ParkedItemSerializer
)

ParkedItemUpdateInputType = generate_input_type_for_serializer(
    'ParkedItemUpdateInputType',
    ParkedItemUpdateSerializer
)

ParkedItemFilterDataType, ParkedItemFilterDataInputType = generate_type_for_filter_set(
    ParkingLotFilter,
    'parking_lot.schema.parking_lot_list',
    'ParkingLotFilterDataType',
    'ParkingLotFilterDataInputType',
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
            instance = ParkedItem.objects.get(id=data['id'])
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
            instance = ParkedItem.objects.get(id=id)
        except ParkedItem.DoesNotExist:
            return DeleteParkedItem(errors=[
                dict(
                    field='nonFieldErrors',
                    messages=gettext('Only creator is allowed to delete the parked item.')
                )
            ])
        instance.delete()
        instance.id = id
        return DeleteParkedItem(result=instance, errors=None, ok=True)


class ExportParkedItem(graphene.Mutation):
    class Arguments:
        filters = ParkedItemFilterDataInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()

    @staticmethod
    def mutate(_, info, filters):
        from apps.contrib.models import ExcelDownload

        serializer = ExcelDownloadSerializer(
            data=dict(
                download_type=int(ExcelDownload.DOWNLOAD_TYPES.PARKING_LOT),
                filters=convert_date_object_to_string_in_dict(filters),
            ),
            context=dict(request=info.context.request)
        )
        if errors := mutation_is_not_valid(serializer):
            return ExportParkedItem(errors=errors, ok=False)
        serializer.save()
        return ExportParkedItem(errors=None, ok=True)


class Mutation(object):
    create_parked_item = CreateParkedItem.Field()
    update_parked_item = UpdateParkedItem.Field()
    delete_parked_item = DeleteParkedItem.Field()
    export_parked_item = ExportParkedItem.Field()
