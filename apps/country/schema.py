from operator import itemgetter

import graphene
from graphene.types.utils import get_type
from graphene_django_extras import (
    DjangoObjectField,
)

from apps.contact.schema import ContactListType
from apps.country.filters import (
    ContextualAnalysisFilter,
    CountryFilter,
    CountryRegionFilter,
    CountrySummaryFilter,
    GeographicalGroupFilter,
    HouseholdSizeFilter,
    MonitoringSubRegionFilter,
)
from apps.country.models import (
    ContextualAnalysis,
    Country,
    CountryRegion,
    CountrySubRegion,
    GeographicalGroup,
    HouseholdSize,
    MonitoringSubRegion,
    Summary,
)
from apps.crisis.enums import CrisisTypeGrapheneEnum
from utils.graphene.enums import EnumDescription
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.pagination import PageGraphqlPaginationWithoutCount
from utils.graphene.relation_loaders import RelationBatchedDjangoObjectType
from utils.graphene.types import CustomDjangoListObjectType

from .enums import HouseholdSizeGapFillingMethodEnum


class MonitoringSubRegionType(RelationBatchedDjangoObjectType):
    class Meta:
        model = MonitoringSubRegion
        exclude_fields = ("portfolios",)

    countries = graphene.Dynamic(lambda: graphene.List(graphene.NonNull(get_type("apps.country.schema.CountryType"))))
    regional_coordinator = graphene.Field("apps.users.schema.PortfolioType")
    monitoring_experts_count = graphene.Int(required=True)
    unmonitored_countries_count = graphene.Int(required=True)
    unmonitored_countries_names = graphene.String(required=True)
    countries_count = graphene.Int(required=True)

    def resolve_countries_count(root, info, **kwargs):
        return info.context.monitoring_sub_region_country_count_loader.load(root.id)

    # countries (reverse FK) is auto-wired via RelationBatchedDjangoObjectType -> ReverseFKListLoader.

    def resolve_regional_coordinator(root, info, **kwargs):
        # was a per-instance Portfolio lookup (N+1); batch via the existing loader keyed by sub-region id
        return info.context.monitoring_subregion_regional_coordinator_loader.load(root.id)


class MonitoringSubRegionListType(CustomDjangoListObjectType):
    class Meta:
        model = MonitoringSubRegion
        filterset_class = MonitoringSubRegionFilter


class CountrySubRegionType(RelationBatchedDjangoObjectType):
    class Meta:
        model = CountrySubRegion


class CountryRegionType(RelationBatchedDjangoObjectType):
    class Meta:
        model = CountryRegion


class CountryRegionListType(CustomDjangoListObjectType):
    class Meta:
        model = CountryRegion
        filterset_class = CountryRegionFilter


class GeographicalGroupType(RelationBatchedDjangoObjectType):
    class Meta:
        model = GeographicalGroup


class GeographicalGroupListType(CustomDjangoListObjectType):
    class Meta:
        model = GeographicalGroup
        filterset_class = GeographicalGroupFilter


class ContextualAnalysisType(RelationBatchedDjangoObjectType):
    class Meta:
        model = ContextualAnalysis
        exclude_fields = ("country",)

    created_by = graphene.Field("apps.users.schema.UserType")
    last_modified_by = graphene.Field("apps.users.schema.UserType")
    crisis_type = graphene.Field(CrisisTypeGrapheneEnum)
    crisis_type_display = EnumDescription(source="get_crisis_type_display")


class ContextualAnalysisListType(CustomDjangoListObjectType):
    class Meta:
        model = ContextualAnalysis
        filterset_class = ContextualAnalysisFilter


class SummaryType(RelationBatchedDjangoObjectType):
    class Meta:
        model = Summary
        exclude_fields = ("country",)

    last_modified_by = graphene.Field("apps.users.schema.UserType")
    created_by = graphene.Field("apps.users.schema.UserType")


class SummaryListType(CustomDjangoListObjectType):
    class Meta:
        model = Summary
        filterset_class = CountrySummaryFilter


class CountryType(RelationBatchedDjangoObjectType):
    class Meta:
        model = Country
        # organizations is unbounded fan-out (420 organizations on the widest country); read them
        # via organizationList(filters: {countries: [id]}), a strict membership test over the M2M
        # through table that reproduces the removed set exactly.
        # The two gidd_* reverses are per-country row sets of the generated GIDD tables --
        # every (year, cause, typology) and every (event, year). Plain lists, so they carry
        # neither pagination nor an ordering bound; excluded for the same reason as figures.
        exclude_fields = (
            "country_conflict",
            "country_disaster",
            "gidd_displacements",
            "gidd_event_displacements",
            "organizations",
        )

    last_summary = graphene.Field(SummaryType)
    last_contextual_analysis = graphene.Field(ContextualAnalysisType)
    contacts = DjangoPaginatedListObjectField(
        ContactListType,
        pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize"),
        related_name="contacts",
        reverse_related_name="country",
    )
    operating_contacts = DjangoPaginatedListObjectField(
        ContactListType,
        pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize"),
        related_name="operating_contacts",
        reverse_related_name="countries_of_operation",
    )
    contextual_analyses = DjangoPaginatedListObjectField(
        ContextualAnalysisListType,
        pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize"),
    )
    summaries = DjangoPaginatedListObjectField(
        SummaryListType,
        pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize"),
    )
    crises = graphene.Dynamic(
        lambda: DjangoPaginatedListObjectField(
            get_type("apps.crisis.schema.CrisisListType"),
            pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize"),
            related_name="crises",
        )
    )
    events = graphene.Dynamic(
        lambda: DjangoPaginatedListObjectField(
            get_type("apps.event.schema.EventListType"),
            pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize"),
            related_name="events",
        )
    )
    entries = graphene.Dynamic(
        lambda: DjangoPaginatedListObjectField(
            get_type("apps.entry.schema.EntryListType"),
            pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize"),
            accessor="entries",
        )
    )
    figures = graphene.Dynamic(
        lambda: DjangoPaginatedListObjectField(
            get_type("apps.entry.schema.FigureListType"),
            pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize"),
            accessor="figures",
        )
    )
    total_flow_conflict = graphene.Int()
    total_flow_disaster = graphene.Int()
    total_stock_conflict = graphene.Int()
    total_stock_disaster = graphene.Int()
    geojson_url = graphene.String()

    regional_coordinator = graphene.Field("apps.users.schema.PortfolioType")
    monitoring_expert = graphene.Field("apps.users.schema.PortfolioType")

    def resolve_last_summary(root, info, **kwargs):
        return info.context.country_last_summary_loader.load(root.id)

    def resolve_last_contextual_analysis(root, info, **kwargs):
        return info.context.country_last_contextual_analysis_loader.load(root.id)

    def resolve_monitoring_expert(root, info, **kwargs):
        return info.context.country_monitoring_expert_loader.load(root.id)

    def resolve_regional_coordinator(root, info, **kwargs):
        if root.monitoring_sub_region_id is None:
            return None
        return info.context.monitoring_subregion_regional_coordinator_loader.load(root.monitoring_sub_region_id)

    def resolve_total_stock_disaster(root, info, **kwargs):
        NULL = "null"
        value = getattr(root, Country.IDP_DISASTER_ANNOTATE, NULL)
        if value != NULL:
            return value
        return info.context.country_total_figure_disaggregation_loader.load(root.id).then(
            itemgetter(Country.IDP_DISASTER_ANNOTATE)
        )

    def resolve_total_stock_conflict(root, info, **kwargs):
        NULL = "null"
        value = getattr(root, Country.IDP_CONFLICT_ANNOTATE, NULL)
        if value != NULL:
            return value
        return info.context.country_total_figure_disaggregation_loader.load(root.id).then(
            itemgetter(Country.IDP_CONFLICT_ANNOTATE)
        )

    def resolve_total_flow_conflict(root, info, **kwargs):
        NULL = "null"
        value = getattr(root, Country.ND_CONFLICT_ANNOTATE, NULL)
        if value != NULL:
            return value
        return info.context.country_total_figure_disaggregation_loader.load(root.id).then(
            itemgetter(Country.ND_CONFLICT_ANNOTATE)
        )

    def resolve_total_flow_disaster(root, info, **kwargs):
        NULL = "null"
        value = getattr(root, Country.ND_DISASTER_ANNOTATE, NULL)
        if value != NULL:
            return value
        return info.context.country_total_figure_disaggregation_loader.load(root.id).then(
            itemgetter(Country.ND_DISASTER_ANNOTATE)
        )

    def resolve_geojson_url(root, info, **kwargs):
        return info.context.request.build_absolute_uri(Country.geojson_url(root.iso3))


class CountryListType(CustomDjangoListObjectType):
    class Meta:
        model = Country
        filterset_class = CountryFilter


class CountryHouseholdSizeType(RelationBatchedDjangoObjectType):
    class Meta:
        model = HouseholdSize

    gap_filling_method = graphene.Field(HouseholdSizeGapFillingMethodEnum)
    gap_filling_method_display = EnumDescription(source="get_gap_filling_method_display")


class HouseholdSizeListType(CustomDjangoListObjectType):
    class Meta:
        model = HouseholdSize
        filterset_class = HouseholdSizeFilter


class Query:
    country = DjangoObjectField(CountryType)
    country_list = DjangoPaginatedListObjectField(
        CountryListType, pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize")
    )
    country_region_list = DjangoPaginatedListObjectField(CountryRegionListType)
    geographical_group_list = DjangoPaginatedListObjectField(GeographicalGroupListType)
    household_size = graphene.Field(
        CountryHouseholdSizeType, country=graphene.ID(required=True), year=graphene.Int(required=True)
    )
    household_size_list = DjangoPaginatedListObjectField(
        HouseholdSizeListType, pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize")
    )
    monitoring_sub_region = DjangoObjectField(MonitoringSubRegionType)
    monitoring_sub_region_list = DjangoPaginatedListObjectField(
        MonitoringSubRegionListType, pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize")
    )

    def resolve_household_size(root, info, country, year):
        try:
            # TODO: Update this query to support dynamic filtering of HouseholdSize in the future
            return HouseholdSize.objects.filter(country=country, year=year, is_active=True).order_by("modified_at").first()
        except HouseholdSize.DoesNotExist:
            return None
