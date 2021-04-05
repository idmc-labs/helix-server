from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField

from apps.contact.schema import ContactListType
from apps.organization.models import Organization, OrganizationKind
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.pagination import PageGraphqlPaginationWithoutCount


class OrganizationType(DjangoObjectType):
    class Meta:
        model = Organization

    contacts = DjangoPaginatedListObjectField(ContactListType,
                                              pagination=PageGraphqlPaginationWithoutCount(
                                                  page_size_query_param='pageSize'
                                              ))


class OrganizationListType(CustomDjangoListObjectType):
    class Meta:
        model = Organization
        filter_fields = {
            'name': ['icontains']
        }


class OrganizationKindObjectType(DjangoObjectType):
    class Meta:
        model = OrganizationKind

    organizations = DjangoPaginatedListObjectField(OrganizationListType,
                                                   pagination=PageGraphqlPaginationWithoutCount(
                                                       page_size_query_param='pageSize'
                                                   ))


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
