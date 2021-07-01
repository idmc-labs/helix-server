from django.conf import settings
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
    CountrySubRegion,
    MonitoringSubRegion,
    ContextualAnalysis,
    Summary,
    HouseholdSize,
    GeographicalGroup,
)
from apps.country.filters import (
    CountryFilter,
    CountryRegionFilter,
    GeographicalGroupFilter,
    MonitoringSubRegionFilter,
)
from apps.crisis.enums import CrisisTypeGrapheneEnum
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.pagination import PageGraphqlPaginationWithoutCount


class MonitoringSubRegionType(DjangoObjectType):
    class Meta:
        model = MonitoringSubRegion
        exclude_fields = ('portfolios',)

    countries = graphene.Dynamic(lambda: DjangoPaginatedListObjectField(
        get_type('apps.country.schema.CountryListType'),
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
        related_name='countries',
    ))
    # TODO: Add dataloaders
    regional_coordinator = graphene.Field('apps.users.schema.PortfolioType')
    monitoring_experts_count = graphene.Int(required=True)
    unmonitored_countries_count = graphene.Int(required=True)
    unmonitored_countries_names = graphene.String(required=True)


class MonitoringSubRegionListType(CustomDjangoListObjectType):
    class Meta:
        model = MonitoringSubRegion
        filterset_class = MonitoringSubRegionFilter


class CountrySubRegionType(DjangoObjectType):
    class Meta:
        model = CountrySubRegion


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
        ),
        related_name='crises',
    ))
    events = graphene.Dynamic(lambda: DjangoPaginatedListObjectField(
        get_type('apps.event.schema.EventListType'),
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
        related_name='events',
    ))
    entries = graphene.Dynamic(lambda: DjangoPaginatedListObjectField(
        get_type('apps.entry.schema.EntryListType'),
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
        accessor='entries',
    ))
    figures = graphene.Dynamic(lambda: DjangoPaginatedListObjectField(
        get_type('apps.entry.schema.FigureListType'),
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
        accessor='figures'
    ))
    total_flow_conflict = graphene.Int()
    total_flow_disaster = graphene.Int()
    total_stock_conflict = graphene.Int()
    total_stock_disaster = graphene.Int()
    geojson_url = graphene.String()

    regional_coordinator = graphene.Field('apps.users.schema.PortfolioType')
    monitoring_expert = graphene.Field('apps.users.schema.PortfolioType')

    def resolve_total_stock_disaster(root, info, **kwargs):
        NULL = 'null'
        value = getattr(
            root,
            Country.IDP_DISASTER_ANNOTATE,
            NULL
        )
        if value != NULL:
            return value
        return info.context.country_country_this_year_idps_disaster_loader.load(root.id)

    def resolve_total_stock_conflict(root, info, **kwargs):
        NULL = 'null'
        value = getattr(
            root,
            Country.IDP_CONFLICT_ANNOTATE,
            NULL
        )
        if value != NULL:
            return value
        return info.context.country_country_this_year_idps_conflict_loader.load(root.id)

    def resolve_total_flow_conflict(root, info, **kwargs):
        NULL = 'null'
        value = getattr(
            root,
            Country.ND_CONFLICT_ANNOTATE,
            NULL
        )
        if value != NULL:
            return value
        return info.context.country_country_this_year_nd_conflict_loader.load(root.id)

    def resolve_total_flow_disaster(root, info, **kwargs):
        NULL = 'null'
        value = getattr(
            root,
            Country.ND_DISASTER_ANNOTATE,
            NULL
        )
        if value != NULL:
            return value
        return info.context.country_country_this_year_nd_disaster_loader.load(root.id)

    def resolve_geojson_url(root, info, **kwargs):
        if 'FileSystemStorage' in settings.DEFAULT_FILE_STORAGE:
            return info.context.request.build_absolute_uri(
                settings.MEDIA_URL +
                Country.geojson_path(root.iso3)
            )
        return info.context.request.build_absolute_uri(Country.geojson_path(root.iso3))


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
    monitoring_sub_region = DjangoObjectField(MonitoringSubRegionType)
    monitoring_sub_region_list = DjangoPaginatedListObjectField(MonitoringSubRegionListType,
                                                                pagination=PageGraphqlPaginationWithoutCount(
                                                                    page_size_query_param='pageSize'
                                                                ))

    def resolve_household_size(root, info, country, year):
        try:
            return HouseholdSize.objects.get(country=country, year=year)
        except HouseholdSize.DoesNotExist:
            return None
