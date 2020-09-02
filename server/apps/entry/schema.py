import graphene
from django.contrib.postgres.fields import JSONField
from graphene import ObjectType
from graphene.types.generic import GenericScalar
from graphene.types.utils import get_type
from graphene_django_extras.converter import convert_django_field
from graphene_django_extras import DjangoObjectType, PageGraphqlPagination, DjangoObjectField

from apps.entry.enums import QuantifierGrapheneEnum, UnitGrapheneEnum, TermGrapheneEnum, TypeGrapheneEnum, \
    RoleGrapheneEnum
from apps.entry.filters import EntryFilter
from apps.entry.models import Figure, Entry
from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType, CustomDjangoListField


@convert_django_field.register(JSONField)
def convert_json_field_to_scalar(field, registry=None):
    # https://github.com/graphql-python/graphene-django/issues/303#issuecomment-339939955
    return GenericScalar()


class DisaggregatedAgeType(ObjectType):
    uuid = graphene.String()
    age_from = graphene.Int()
    age_to = graphene.Int()
    value = graphene.Int()


class DisaggregatedStratumType(ObjectType):
    uuid = graphene.String()
    date = graphene.String()  # because inside the json field
    value = graphene.Int()


class FigureType(DjangoObjectType):
    class Meta:
        model = Figure

    quantifier = graphene.Field(QuantifierGrapheneEnum)
    unit = graphene.Field(UnitGrapheneEnum)
    term = graphene.Field(TermGrapheneEnum)
    type = graphene.Field(TypeGrapheneEnum)
    role = graphene.Field(RoleGrapheneEnum)
    age_json = graphene.List(DisaggregatedAgeType)
    strata_json = graphene.List(DisaggregatedStratumType)


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

    created_by = graphene.Field('apps.users.schema.UserType')
    last_modified_by = graphene.Field('apps.users.schema.UserType')
    figures = DjangoPaginatedListObjectField(FigureListType,
                                             pagination=PageGraphqlPagination(
                                                 page_size_query_param='perPage'
                                             ))
    reviewers = CustomDjangoListField('apps.users.schema.UserType')
    total_figures = graphene.Field(graphene.Int)


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
