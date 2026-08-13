import graphene
from graphene_django_extras import DjangoObjectField

from apps.contact.schema import ContactListType
from apps.country.schema import CountryType
from apps.organization.enums import OrganizationCategoryTypeGrapheneEnum, OrganizationReliablityEnum
from apps.organization.filters import OrganizationFilter, OrganizationKindFilter
from apps.organization.models import Organization, OrganizationKind
from utils.graphene.enums import EnumDescription
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.pagination import PageGraphqlPaginationWithoutCount
from utils.graphene.relation_loaders import RelationBatchedDjangoObjectType
from utils.graphene.types import CustomDjangoListObjectType


class OrganizationType(RelationBatchedDjangoObjectType):
    class Meta:
        model = Organization
        # sourced_figures and published_entries are unbounded fan-out (one organization sources
        # 15,312 figures and publishes 3,321 entries); read them via
        # figureList(filters: {filterFigureSources: [id]}) and
        # entryList(filters: {filterEntryPublishers: [id]}). Both are strict membership tests over
        # the M2M through table and reproduce the removed sets exactly.
        # sourced_report, published_report, sourced_extractionquery and published_extractionquery
        # are this organization's appearances in the stored figure filter of a report or a saved
        # extraction query; reportList and extractionQueryList cannot filter on that selection, so
        # those four have no bounded replacement.
        # sub_organizations is the reverse of Organization.parent and OrganizationFilter has no
        # parent filter, so it has no bounded replacement either.
        exclude_fields = (
            "sourced_figures",
            "published_entries",
            "sourced_report",
            "published_report",
            "sourced_extractionquery",
            "published_extractionquery",
            "sub_organizations",
        )

    category = graphene.Field(OrganizationCategoryTypeGrapheneEnum)
    category_display = EnumDescription(source="get_category_display")
    contacts = DjangoPaginatedListObjectField(
        ContactListType, pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize")
    )
    organization_kind = graphene.Field("apps.organization.schema.OrganizationKindObjectType")
    countries = graphene.List(graphene.NonNull(CountryType), required=True)

    # organization_kind (forward FK) + countries (M2M) are auto-wired via
    # RelationBatchedDjangoObjectType -> RelationNodeLoader / M2MListLoader.


class OrganizationListType(CustomDjangoListObjectType):
    class Meta:
        filterset_class = OrganizationFilter
        model = Organization


class OrganizationKindObjectType(RelationBatchedDjangoObjectType):
    class Meta:
        model = OrganizationKind

    organizations = DjangoPaginatedListObjectField(
        OrganizationListType, pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize")
    )
    reliability = graphene.Field(OrganizationReliablityEnum)
    reliability_display = EnumDescription(source="get_reliability_display_display")


class OrganizationKindListType(CustomDjangoListObjectType):
    class Meta:
        model = OrganizationKind
        filterset_class = OrganizationKindFilter


class Query:
    organization = DjangoObjectField(OrganizationType)
    organization_list = DjangoPaginatedListObjectField(
        OrganizationListType, pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize")
    )
    organization_kind = DjangoObjectField(OrganizationKindObjectType)
    organization_kind_list = DjangoPaginatedListObjectField(
        OrganizationKindListType, pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize")
    )
