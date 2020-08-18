from graphene_django_extras import DjangoObjectType, PageGraphqlPagination, \
    DjangoListObjectType, DjangoObjectField

from apps.contact.schema import ContactListType
from apps.organization.models import Organization, OrganizationKind
from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType


class OrganizationType(DjangoObjectType):
    class Meta:
        model = Organization

    contacts = DjangoPaginatedListObjectField(ContactListType)


class OrganizationListType(CustomDjangoListObjectType):
    class Meta:
        model = Organization
        filter_fields = {
            'short_name': ['icontains']
        }
        pagination = PageGraphqlPagination(page_size_query_param='pageSize')


class OrganizationKindObjectType(DjangoObjectType):
    class Meta:
        model = OrganizationKind

    organizations = DjangoPaginatedListObjectField(OrganizationListType)


class OrganizationKindListType(CustomDjangoListObjectType):
    class Meta:
        model = OrganizationKind
        pagination = PageGraphqlPagination(page_size_query_param='pageSize')


class Query:
    organization = DjangoObjectField(OrganizationType)
    organization_list = DjangoPaginatedListObjectField(OrganizationListType)
    organization_kind = DjangoObjectField(OrganizationKindObjectType)
    organization_kind_list = DjangoPaginatedListObjectField(OrganizationKindListType)
