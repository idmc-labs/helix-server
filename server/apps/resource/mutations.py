from django.db.models import ProtectedError
from django.utils.translation import gettext
import graphene

from apps.resource.models import Resource, ResourceGroup
from apps.resource.schema import ResourceType, ResourceGroupType
from apps.resource.serializers import ResourceSerializer, ResourceGroupSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker


class ResourceCreateInputType(graphene.InputObjectType):
    name = graphene.String(required=True)
    url = graphene.String(required=True)
    group = graphene.String(required=True)
    countries = graphene.List(graphene.ID)
    last_accessed_on = graphene.String(required=False)


class ResourceUpdateInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    name = graphene.String()
    url = graphene.String()
    group = graphene.String()
    countries = graphene.List(graphene.ID)
    last_accessed_on = graphene.String()


class CreateResource(graphene.Mutation):
    class Arguments:
        resource = ResourceCreateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    resource = graphene.Field(ResourceType)

    @staticmethod
    @permission_checker(['resource.add_resource'])
    def mutate(root, info, resource):
        serializer = ResourceSerializer(data=resource,
                                        context={'request': info.context})
        if errors := mutation_is_not_valid(serializer):
            return CreateResource(errors=errors, ok=False)
        instance = serializer.save()
        return CreateResource(resource=instance, errors=None, ok=True)


class UpdateResource(graphene.Mutation):
    class Arguments:
        resource = ResourceUpdateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    resource = graphene.Field(ResourceType)

    @staticmethod
    @permission_checker(['resource.change_resource'])
    def mutate(root, info, resource):
        try:
            instance = Resource.objects.get(id=resource['id'], created_by=info.context.user)
        except Resource.DoesNotExist:
            return UpdateResource(errors=[
                CustomErrorType(field='non_field_errors', messages=gettext('Resource does not exist.'))
            ])
        serializer = ResourceSerializer(instance=instance,
                                        data=resource,
                                        context={'request': info.context},
                                        partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateResource(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateResource(resource=instance, errors=None, ok=True)


class DeleteResource(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    resource = graphene.Field(ResourceType)

    @staticmethod
    @permission_checker(['resource.delete_resource'])
    def mutate(root, info, id):
        try:
            instance = Resource.objects.get(id=id, created_by=info.context.user)
        except Resource.DoesNotExist:
            return UpdateResource(errors=[
                CustomErrorType(field='non_field_errors', messages=gettext('Resource does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteResource(resource=instance, errors=None, ok=True)


class ResourceGroupCreateInputType(graphene.InputObjectType):
    name = graphene.String(required=True)


class ResourceGroupUpdateInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    name = graphene.String()


class CreateResourceGroup(graphene.Mutation):
    class Arguments:
        resource_group = ResourceGroupCreateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    resource_group = graphene.Field(ResourceGroupType)

    @staticmethod
    @permission_checker(['resource.add_resource'])
    def mutate(root, info, resource_group):
        serializer = ResourceGroupSerializer(data=resource_group,
                                             context={'request': info.context})
        if errors := mutation_is_not_valid(serializer):
            return CreateResourceGroup(errors=errors, ok=False)
        instance = serializer.save()
        return CreateResourceGroup(resource_group=instance, errors=None, ok=True)


class UpdateResourceGroup(graphene.Mutation):
    class Arguments:
        resource_group = ResourceGroupUpdateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    resource_group = graphene.Field(ResourceGroupType)

    @staticmethod
    @permission_checker(['resource.change_resource'])
    def mutate(root, info, resource_group):
        try:
            instance = ResourceGroup.objects.get(id=resource_group['id'], created_by=info.context.user)
        except ResourceGroup.DoesNotExist:
            return UpdateResourceGroup(errors=[
                CustomErrorType(field='non_field_errors', messages=gettext('ResourceGroup does not exist.'))
            ])
        serializer = ResourceGroupSerializer(instance=instance,
                                             data=resource_group,
                                             context={'request': info.context},
                                             partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateResourceGroup(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateResourceGroup(resource_group=instance, errors=None, ok=True)


class DeleteResourceGroup(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    resource_group = graphene.Field(ResourceGroupType)

    @staticmethod
    @permission_checker(['resource.delete_resource'])
    def mutate(root, info, id):
        try:
            instance = ResourceGroup.objects.get(id=id, created_by=info.context.user)
        except ResourceGroup.DoesNotExist:
            return DeleteResourceGroup(errors=[
                CustomErrorType(field='non_field_errors', messages=gettext('ResourceGroup does not exist.'))
            ])
        can_delete, msg = instance.can_delete()
        if not can_delete:
            return DeleteResourceGroup(errors=[
                CustomErrorType(field='non_field_errors', messages=msg)
            ])
        instance.delete()
        instance.id = id
        return DeleteResourceGroup(resource_group=instance, errors=None, ok=True)


class Mutation:
    create_resource = CreateResource.Field()
    update_resource = UpdateResource.Field()
    delete_resource = DeleteResource.Field()
    create_resource_group = CreateResourceGroup.Field()
    update_resource_group = UpdateResourceGroup.Field()
    delete_resource_group = DeleteResourceGroup.Field()
