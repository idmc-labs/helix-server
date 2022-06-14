import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField

from apps.contact.schema import ContactListType
from apps.organization.models import Organization, OrganizationKind
from apps.organization.enums import (
    OrganizationCategoryTypeGrapheneEnum, OrganizationReliablityEnum
)
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.pagination import PageGraphqlPaginationWithoutCount
from apps.organization.filters import OrganizationFilter


class OrganizationType(DjangoObjectType):
    class Meta:
        model = Organization

    category = graphene.Field(OrganizationCategoryTypeGrapheneEnum)
    contacts = DjangoPaginatedListObjectField(ContactListType,
                                              pagination=PageGraphqlPaginationWithoutCount(
                                                  page_size_query_param='pageSize'
                                              ))


class OrganizationListType(CustomDjangoListObjectType):
    class Meta:
        filterset_class = OrganizationFilter
        model = Organization


class OrganizationKindObjectType(DjangoObjectType):
    class Meta:
        model = OrganizationKind

    organizations = DjangoPaginatedListObjectField(OrganizationListType,
                                                   pagination=PageGraphqlPaginationWithoutCount(
                                                       page_size_query_param='pageSize'
                                                   ))
    reliability = graphene.Field(OrganizationReliablityEnum)


class OrganizationKindListType(CustomDjangoListObjectType):
    class Meta:
        model = OrganizationKind


class Query:
    organization = DjangoObjectField(OrganizationType)
    organization_list = DjangoPaginatedListObjectField(OrganizationListType,
                                                       pagination=PageGraphqlPaginationWithoutCount(
                                                           page_size_query_param='pageSize'
                                                       ))
    organization_kind = DjangoObjectField(OrganizationKindObjectType)
    organization_kind_list = DjangoPaginatedListObjectField(OrganizationKindListType,
                                                            pagination=PageGraphqlPaginationWithoutCount(
                                                                page_size_query_param='pageSize'
                                                            ))
