import graphene
from graphene_django_extras import DjangoObjectType, PageGraphqlPagination, DjangoObjectField

from apps.entry.enums import QuantifierGrapheneEnum, UnitGrapheneEnum, TermGrapheneEnum, TypeGrapheneEnum, \
    RoleGrapheneEnum
from apps.entry.filters import EntryFilter
from apps.entry.models import Figure, Entry
from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType


class FigureType(DjangoObjectType):
    class Meta:
        model = Figure

    quantifier = graphene.Field(QuantifierGrapheneEnum)
    unit = graphene.Field(UnitGrapheneEnum)
    term = graphene.Field(TermGrapheneEnum)
    type = graphene.Field(TypeGrapheneEnum)
    role = graphene.Field(RoleGrapheneEnum)


class FigureListType(CustomDjangoListObjectType):
    class Meta:
        model = Figure
        filter_fields = {
            'unit': ('exact',),
            'start_date': ('lte', 'gte'),
        }


class EntryType(DjangoObjectType):
    class Meta:
        model = Entry

    figures = DjangoPaginatedListObjectField(FigureListType,
                                             pagination=PageGraphqlPagination(
                                                 page_size_query_param='perPage'
                                             ))


class EntryListType(CustomDjangoListObjectType):
    class Meta:
        model = Entry
        filterset_class = EntryFilter


class Query:
    figure = DjangoObjectField(FigureType)
    figure_list = DjangoPaginatedListObjectField(FigureListType,
                                                 pagination=PageGraphqlPagination(
                                                     page_size_query_param='pageSize'
                                                 ))
    entry = DjangoObjectField(EntryType)
    entry_list = DjangoPaginatedListObjectField(EntryListType,
                                                pagination=PageGraphqlPagination(
                                                    page_size_query_param='pageSize'
                                                ))
