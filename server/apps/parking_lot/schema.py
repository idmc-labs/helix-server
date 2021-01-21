import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import PageGraphqlPagination, DjangoObjectField

from apps.parking_lot.models import ParkingLot
from apps.parking_lot.enums import ParkingLotGrapheneEnum
from apps.parking_lot.filters import ParkingLotFilter
from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType


class ParkingLotType(DjangoObjectType):
    class Meta:
        model = ParkingLot

    status = graphene.Field(ParkingLotGrapheneEnum)


class ParkingLotListType(CustomDjangoListObjectType):
    class Meta:
        model = ParkingLot
        filterset_class = ParkingLotFilter


class Query:
    parking_lot = DjangoObjectField(ParkingLotType)
    parking_lot_list = DjangoPaginatedListObjectField(ParkingLotListType,
                                                      pagination=PageGraphqlPagination(
                                                          page_size_query_param='pageSize'
                                                      ))
