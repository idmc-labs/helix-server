from graphene_django import DjangoObjectType
from graphene_django_extras import PageGraphqlPagination, DjangoObjectField

from apps.resource.models import Resource, ResourceGroup
from apps.resource.filters import ResourceFilter, ResourceGroupFilter
from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType


class ResourceType(DjangoObjectType):
    class Meta:
        model = Resource


class ResourceListType(CustomDjangoListObjectType):
    class Meta:
        model = Resource
        filterset_class = ResourceFilter


class ResourceGroupType(DjangoObjectType):
    class Meta:
        model = ResourceGroup

    resources = DjangoPaginatedListObjectField(ResourceListType,
                                               pagination=PageGraphqlPagination(
                                                   page_size_query_param='pageSize'
                                               ))


class ResourceGroupListType(CustomDjangoListObjectType):
    class Meta:
        model = ResourceGroup
        filterset_class = ResourceGroupFilter


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
