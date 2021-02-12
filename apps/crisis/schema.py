import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import PageGraphqlPagination, DjangoObjectField

from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.crisis.filters import CrisisFilter
from apps.crisis.models import Crisis
from apps.event.schema import EventListType
from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType


class CrisisType(DjangoObjectType):
    class Meta:
        model = Crisis

    crisis_type = graphene.Field(CrisisTypeGrapheneEnum)
    events = DjangoPaginatedListObjectField(EventListType,
                                            pagination=PageGraphqlPagination(
                                                page_size_query_param='pageSize'
                                            ))
    total_stock_figures = graphene.Field(graphene.Int)
    total_flow_figures = graphene.Field(graphene.Int)


class CrisisListType(CustomDjangoListObjectType):
    class Meta:
        model = Crisis
        filterset_class = CrisisFilter


class Query:
    crisis = DjangoObjectField(CrisisType)
    crisis_list = DjangoPaginatedListObjectField(CrisisListType,
                                                 pagination=PageGraphqlPagination(
                                                     page_size_query_param='pageSize'
                                                 ))
