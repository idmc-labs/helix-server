from graphene_django_extras import DjangoObjectType, DjangoFilterPaginateListField, PageGraphqlPagination, \
    DjangoListObjectType, DjangoListObjectField

from apps.contact.schema import ContactType
from apps.organization.models import Organization


class OrganizationType(DjangoObjectType):
    class Meta:
        model = Organization

    contacts = DjangoFilterPaginateListField(ContactType,
                                             pagination=PageGraphqlPagination(page_size_query_param='pageSize'))


class OrganizationListType(DjangoListObjectType):
    class Meta:
        model = Organization
        # filterset_class =
        pagination = PageGraphqlPagination(page_size_query_param='pageSize')


class Query:
    organization = DjangoListObjectField(OrganizationType)
    organization_list = DjangoListObjectField(OrganizationListType)
