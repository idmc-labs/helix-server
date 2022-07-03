import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField
from apps.resource.models import Resource, ResourceGroup


class ResourceType(DjangoObjectType):
    class Meta:
        model = Resource


class ResourceGroupType(DjangoObjectType):
    class Meta:
        model = ResourceGroup


class Query:
    resource = DjangoObjectField(ResourceType)
    resource_list = graphene.List(ResourceType)
    resource_group = DjangoObjectField(ResourceType)
    resource_group_list = graphene.List(ResourceGroupType)

    def resolve_resource_list(root, info, **kwargs):
        return Resource.objects.filter(created_by=info.context.user)

    def resolve_resource_group_list(root, info, **kwargs):
        return ResourceGroup.objects.filter(created_by=info.context.user)
