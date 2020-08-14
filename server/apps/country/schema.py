from graphene_django_extras import DjangoObjectType, PageGraphqlPagination, \
    DjangoListObjectType, DjangoListObjectField

from apps.country.models import Country


class CountryType(DjangoObjectType):
    class Meta:
        model = Country


class CountryListType(DjangoListObjectType):
    class Meta:
        model = Country
        filter_fields = {
            'name': ['icontains']
        }
        pagination = PageGraphqlPagination(page_size_query_param='pageSize')


class Query:
    country = DjangoListObjectField(CountryType)
    country_list = DjangoListObjectField(CountryListType)
