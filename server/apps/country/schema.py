from graphene_django_extras import DjangoObjectType, PageGraphqlPagination, \
    DjangoObjectField

from apps.contact.schema import ContactListType
from apps.country.models import Country, CountryRegion
from apps.organization.schema import OrganizationListType
from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType


class CountryRegionType(DjangoObjectType):
    class Meta:
        model = CountryRegion


class CountryType(DjangoObjectType):
    class Meta:
        model = Country

    contacts = DjangoPaginatedListObjectField(ContactListType,
                                              pagination=PageGraphqlPagination(
                                                  page_size_query_param='pageSize'
                                              ), accessor='contacts')
    operating_contacts = DjangoPaginatedListObjectField(ContactListType,
                                                        pagination=PageGraphqlPagination(
                                                            page_size_query_param='pageSize'
                                                        ), accessor='operating_contacts')

    @staticmethod
    def get_queryset(queryset, info):
        # graphene_django/fields.py:57 demands we implement this method
        # so that we can filter based on request, but we do not need
        return queryset


class CountryListType(CustomDjangoListObjectType):
    class Meta:
        model = Country
        filter_fields = {
            'name': ['icontains']
        }


class Query:
    country = DjangoObjectField(CountryType)
    country_list = DjangoPaginatedListObjectField(CountryListType,
                                                  pagination=PageGraphqlPagination(
                                                      page_size_query_param='pageSize'
                                                  ))
