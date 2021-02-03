import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import PageGraphqlPagination, DjangoObjectField

from apps.parking_lot.models import ParkedItem
from apps.parking_lot.enums import ParkedItemGrapheneEnum
from apps.parking_lot.filters import ParkingLotFilter
from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType


class ParkedItemType(DjangoObjectType):
    class Meta:
        model = ParkedItem

    status = graphene.Field(ParkedItemGrapheneEnum)
    entry = graphene.Field('apps.entry.schema.EntryType')


class ParkedItemListType(CustomDjangoListObjectType):
    class Meta:
        model = ParkedItem
        filterset_class = ParkingLotFilter


class Query:
    parked_item = DjangoObjectField(ParkedItemType)
    parked_item_list = DjangoPaginatedListObjectField(ParkedItemListType,
                                                      pagination=PageGraphqlPagination(
                                                          page_size_query_param='pageSize'
                                                      ))
