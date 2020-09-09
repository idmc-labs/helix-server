from graphene_django_extras import DjangoObjectType, PageGraphqlPagination, \
    DjangoListObjectType, DjangoListObjectField, DjangoObjectField

from apps.resource.models import Resource, ResourceGroup
from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType


class ResourceType(DjangoObjectType):
    class Meta:
        model = Resource


class ResourceListType(CustomDjangoListObjectType):
    class Meta:
        model = Resource
        filter_fields = {
            'name': ['icontains']
        }


class ResourceGroupType(DjangoObjectType):
    class Meta:
        model = ResourceGroup


class ResourceGroupListType(CustomDjangoListObjectType):
    class Meta:
        model = ResourceGroup
        filter_fields = {
            'name': ['icontains']
        }

    resources = DjangoPaginatedListObjectField(ResourceListType,
                                               pagination=PageGraphqlPagination(
                                                   page_size_query_param='pageSize'
                                               ))


class Query:
    resource = DjangoObjectField(ResourceType)
    resource_list = DjangoPaginatedListObjectField(ResourceListType,
                                                   pagination=PageGraphqlPagination(
                                                       page_size_query_param='pageSize'
                                                   ))
    resource_group = DjangoObjectField(ResourceGroupType)
    resource_group_list = DjangoPaginatedListObjectField(ResourceGroupListType,
                                                         pagination=PageGraphqlPagination(
                                                             page_size_query_param='pageSize'
                                                         ))
