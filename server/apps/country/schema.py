from graphene_django_extras import DjangoObjectType, PageGraphqlPagination, \
    DjangoListObjectType, DjangoListObjectField, DjangoObjectField

from apps.country.models import Country
from apps.organization.schema import OrganizationListType
from utils.fields import DjangoPaginatedListObjectField


class CountryType(DjangoObjectType):
    class Meta:
        model = Country

    organizations = DjangoPaginatedListObjectField(OrganizationListType)


class CountryListType(DjangoListObjectType):
    class Meta:
        model = Country
        filter_fields = {
            'name': ['icontains']
        }
        pagination = PageGraphqlPagination(page_size_query_param='pageSize')


class Query:
    country = DjangoObjectField(CountryType)
    country_list = DjangoListObjectField(CountryListType)
