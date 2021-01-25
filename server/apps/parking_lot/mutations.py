import graphene
from django.utils.translation import gettext

from apps.parking_lot.models import ParkingLot
from apps.parking_lot.schema import ParkingLotType
from apps.parking_lot.serializers import ParkingLotSerializer
from apps.parking_lot.enums import ParkingLotGrapheneEnum
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker


class ParkingLotCreateInputType(graphene.InputObjectType):
    country = graphene.ID(required=True)
    title = graphene.String(required=True)
    url = graphene.String(required=True)
    assigned_to = graphene.ID(required=False)
    status = graphene.NonNull(ParkingLotGrapheneEnum)
    comments = graphene.String(required=False)


class ParkingLotUpdateInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    country = graphene.ID()
    title = graphene.String()
    url = graphene.String()
    assigned_to = graphene.ID()
    status = graphene.Field(ParkingLotGrapheneEnum)
    comments = graphene.String()


class CreateParkingLot(graphene.Mutation):
    class Arguments:
        data = ParkingLotCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ParkingLotType)

    @staticmethod
    @permission_checker(['parking_lot.add_parkinglot'])
    def mutate(root, info, data):
        serializer = ParkingLotSerializer(data=data, context=dict(request=info.context))
        if errors := mutation_is_not_valid(serializer):
            return CreateParkingLot(errors=errors, ok=False)
        instance = serializer.save()
        return CreateParkingLot(result=instance, errors=None, ok=True)


class UpdateParkingLot(graphene.Mutation):
    class Arguments:
        data = ParkingLotUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ParkingLotType)

    @staticmethod
    @permission_checker(['parking_lot.change_parkinglot'])
    def mutate(root, info, data):
        try:
            instance = ParkingLot.objects.get(id=data['id'], created_by=info.context.user)
        except ParkingLot.DoesNotExist:
            return UpdateParkingLot(errors=[
                dict(field='nonFieldErrors', messages=gettext('Parked item does not exist.'))
            ])
        serializer = ParkingLotSerializer(instance=instance, data=data, partial=True,
                                          context=dict(request=info.context))
        if errors := mutation_is_not_valid(serializer):
            return UpdateParkingLot(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateParkingLot(result=instance, errors=None, ok=True)


class DeleteParkingLot(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ParkingLotType)

    @staticmethod
    @permission_checker(['parking_lot.delete_parkinglot'])
    def mutate(root, info, id):
        try:
            instance = ParkingLot.objects.get(id=id, created_by=info.context.user)
        except ParkingLot.DoesNotExist:
            return DeleteParkingLot(errors=[
                dict(field='nonFieldErrors', messages=gettext('Parked item does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteParkingLot(result=instance, errors=None, ok=True)


class Mutation(object):
    create_parking_lot = CreateParkingLot.Field()
    update_parking_lot = UpdateParkingLot.Field()
    delete_parking_lot = DeleteParkingLot.Field()
