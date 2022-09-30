import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField
from utils.graphene.enums import EnumDescription

from apps.parking_lot.models import ParkedItem
from apps.parking_lot.enums import (
    ParkingLotStatusGrapheneEnum,
    ParkingLotSourceGrapheneEnum,
)
from apps.parking_lot.filters import ParkingLotFilter
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.pagination import PageGraphqlPaginationWithoutCount


class ParkedItemType(DjangoObjectType):
    class Meta:
        model = ParkedItem

    status = graphene.Field(ParkingLotStatusGrapheneEnum)
    status_display = EnumDescription(source='get_status_display')
    source = graphene.Field(ParkingLotSourceGrapheneEnum)
    source_display = EnumDescription(source='get_source_display')
    entry = graphene.Field('apps.entry.schema.EntryType')


class ParkedItemListType(CustomDjangoListObjectType):
    class Meta:
        model = ParkedItem
        filterset_class = ParkingLotFilter


class Query:
    parked_item = DjangoObjectField(ParkedItemType)
    parked_item_list = DjangoPaginatedListObjectField(ParkedItemListType,
                                                      pagination=PageGraphqlPaginationWithoutCount(
                                                          page_size_query_param='pageSize'
                                                      ))
