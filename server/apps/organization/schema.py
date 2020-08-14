from graphene_django_extras import DjangoObjectType, PageGraphqlPagination, \
    DjangoListObjectType, DjangoObjectField

from apps.contact.schema import ContactListType
from apps.organization.models import Organization
from utils.fields import DjangoPaginatedListObjectField


class OrganizationType(DjangoObjectType):
    class Meta:
        model = Organization

    contacts = DjangoPaginatedListObjectField(ContactListType)


class OrganizationListType(DjangoListObjectType):
    class Meta:
        model = Organization
        # filterset_class =
        pagination = PageGraphqlPagination(page_size_query_param='pageSize')


class Query:
    organization = DjangoObjectField(OrganizationType)
    organization_list = DjangoPaginatedListObjectField(OrganizationListType)
