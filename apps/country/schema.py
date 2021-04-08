import graphene
from graphene.types.utils import get_type
from graphene_django import DjangoObjectType
from graphene_django_extras import (
    DjangoObjectField,
)

from apps.contact.schema import ContactListType
from apps.country.models import (
    Country,
    CountryRegion,
    ContextualAnalysis,
    Summary,
    HouseholdSize,
    GeographicalGroup,
)
from apps.country.filters import (
    CountryFilter,
    CountryRegionFilter,
    GeographicalGroupFilter,
)
from apps.crisis.enums import CrisisTypeGrapheneEnum
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.pagination import PageGraphqlPaginationWithoutCount


class CountryRegionType(DjangoObjectType):
    class Meta:
        model = CountryRegion


class CountryRegionListType(CustomDjangoListObjectType):
    class Meta:
        model = CountryRegion
        filterset_class = CountryRegionFilter


class GeographicalGroupType(DjangoObjectType):
    class Meta:
        model = GeographicalGroup


class GeographicalGroupListType(CustomDjangoListObjectType):
    class Meta:
        model = GeographicalGroup
        filterset_class = GeographicalGroupFilter


class ContextualAnalysisType(DjangoObjectType):
    class Meta:
        model = ContextualAnalysis
        exclude_fields = ('country',)

    created_by = graphene.Field('apps.users.schema.UserType')
    last_modified_by = graphene.Field('apps.users.schema.UserType')
    crisis_type = graphene.Field(CrisisTypeGrapheneEnum)


class ContextualAnalysisListType(CustomDjangoListObjectType):
    class Meta:
        model = ContextualAnalysis
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
    last_contextual_analysis = graphene.Field(ContextualAnalysisType)
    contacts = DjangoPaginatedListObjectField(
        ContactListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
        related_name='contacts',
        reverse_related_name='country',
    )
    operating_contacts = DjangoPaginatedListObjectField(
        ContactListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
        related_name='operating_contacts',
        reverse_related_name='countries_of_operation',
    )
    contextual_analyses = DjangoPaginatedListObjectField(
        ContextualAnalysisListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
    )
    summaries = DjangoPaginatedListObjectField(
        SummaryListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
    )
    crises = graphene.Dynamic(lambda: DjangoPaginatedListObjectField(
        get_type('apps.crisis.schema.CrisisListType'),
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ))
    )
    events = graphene.Dynamic(lambda: DjangoPaginatedListObjectField(
        get_type('apps.event.schema.EventListType'),
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        )))
    crises_count = graphene.Int()
    events_count = graphene.Int()
    entries = graphene.Dynamic(lambda: DjangoPaginatedListObjectField(
        get_type('apps.entry.schema.EntryListType'),
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
        accessor='entries',
    ))
    """
    related_name='events__entries',
    reverse_related_name='event__countries',
    """
    figures = graphene.Dynamic(lambda: DjangoPaginatedListObjectField(
        get_type('apps.entry.schema.FigureListType'),
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
    ))

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
                                                  pagination=PageGraphqlPaginationWithoutCount(
                                                      page_size_query_param='pageSize'
                                                  ))
    country_region_list = DjangoPaginatedListObjectField(CountryRegionListType)
    geographical_group_list = DjangoPaginatedListObjectField(GeographicalGroupListType)
    household_size = graphene.Field(CountryHouseholdSizeType,
                                    country=graphene.ID(required=True),
                                    year=graphene.Int(required=True))

    def resolve_household_size(root, info, country, year):
        try:
            return HouseholdSize.objects.get(country=country, year=year)
        except HouseholdSize.DoesNotExist:
            return None
