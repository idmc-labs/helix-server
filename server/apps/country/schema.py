import graphene
from graphene.types.utils import get_type
from graphene_django import DjangoObjectType
from graphene_django_extras import (
    PageGraphqlPagination,
    DjangoObjectField
)

from apps.contact.schema import ContactListType
from apps.country.models import Country, CountryRegion, ContextualUpdate, Summary, HouseholdSize
from apps.country.filters import CountryFilter
from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType


class CountryRegionType(DjangoObjectType):
    class Meta:
        model = CountryRegion


class CountryRegionListType(CustomDjangoListObjectType):
    class Meta:
        model = CountryRegion
        filter_fields = {
            'name': ('icontains',),
        }


class ContextualUpdateType(DjangoObjectType):
    class Meta:
        model = ContextualUpdate
        exclude_fields = ('country',)

    created_by = graphene.Field('apps.users.schema.UserType')
    last_modified_by = graphene.Field('apps.users.schema.UserType')


class ContextualUpdateListType(CustomDjangoListObjectType):
    class Meta:
        model = ContextualUpdate
        filter_fields = {
            'created_at': ['lte', 'gte']
        }


class SummaryType(DjangoObjectType):
    class Meta:
        model = Summary
        exclude_fields = ('country',)

    last_modified_by = graphene.Field('apps.users.schema.UserType')
    created_by = graphene.Field('apps.users.schema.UserType')


class SummaryListType(CustomDjangoListObjectType):
    class Meta:
        model = Summary
        filter_fields = {
            'created_at': ['lte', 'gte']
        }


class CountryType(DjangoObjectType):
    class Meta:
        model = Country
        filter_fields = {}

    last_summary = graphene.Field(SummaryType)
    last_contextual_update = graphene.Field(ContextualUpdateType)
    contacts = DjangoPaginatedListObjectField(ContactListType,
                                              pagination=PageGraphqlPagination(
                                                  page_size_query_param='pageSize'
                                              ), accessor='contacts')
    operating_contacts = DjangoPaginatedListObjectField(ContactListType,
                                                        pagination=PageGraphqlPagination(
                                                            page_size_query_param='pageSize'
                                                        ), accessor='operating_contacts')
    contextual_updates = DjangoPaginatedListObjectField(ContextualUpdateListType,
                                                        pagination=PageGraphqlPagination(
                                                            page_size_query_param='pageSize'
                                                        ), accessor='contextual_updates')
    summaries = DjangoPaginatedListObjectField(SummaryListType,
                                               pagination=PageGraphqlPagination(
                                                   page_size_query_param='pageSize'
                                               ), accessor='summaries')
    crises = graphene.Dynamic(lambda: DjangoPaginatedListObjectField(
        get_type('apps.crisis.schema.CrisisListType'),
        pagination=PageGraphqlPagination(
            page_size_query_param='pageSize'
        ), accessor='crises'))
    entries = graphene.Dynamic(lambda: DjangoPaginatedListObjectField(
        get_type('apps.entry.schema.EntryListType'),
        pagination=PageGraphqlPagination(
            page_size_query_param='pageSize'
        ), accessor='entries'))

    @staticmethod
    def get_queryset(queryset, info):
        # graphene_django/fields.py:57 demands we implement this method
        # so that we can filter based on request, but we do not need
        return queryset


class CountryListType(CustomDjangoListObjectType):
    class Meta:
        model = Country
        filterset_class = CountryFilter


class CountryHouseholdSizeType(DjangoObjectType):
    class Meta:
        model = HouseholdSize


class Query:
    country = DjangoObjectField(CountryType)
    country_list = DjangoPaginatedListObjectField(CountryListType,
                                                  pagination=PageGraphqlPagination(
                                                      page_size_query_param='pageSize'
                                                  ))
    country_region_list = DjangoPaginatedListObjectField(CountryRegionListType)
    household_size = graphene.Field(CountryHouseholdSizeType,
                                    country=graphene.ID(required=True),
                                    year=graphene.Int(required=True))

    def resolve_household_size(root, info, country, year):
        try:
            return HouseholdSize.objects.get(country=country, year=year)
        except HouseholdSize.DoesNotExist:
            return None
