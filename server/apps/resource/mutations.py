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
    group = graphene.ID()
    countries = graphene.NonNull(graphene.List(graphene.NonNull(graphene.ID)))
    last_accessed_on = graphene.DateTime(required=False)


class ResourceUpdateInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    name = graphene.String()
    url = graphene.String()
    group = graphene.ID()
    countries = graphene.List(graphene.NonNull(graphene.ID))
    last_accessed_on = graphene.DateTime()


class CreateResource(graphene.Mutation):
    class Arguments:
        data = ResourceCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ResourceType)

    @staticmethod
    @permission_checker(['resource.add_resource'])
    def mutate(root, info, data):
        serializer = ResourceSerializer(data=data,
                                        context={'request': info.context})
        if errors := mutation_is_not_valid(serializer):
            return CreateResource(errors=errors, ok=False)
        instance = serializer.save()
        return CreateResource(result=instance, errors=None, ok=True)


class UpdateResource(graphene.Mutation):
    class Arguments:
        data = ResourceUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ResourceType)

    @staticmethod
    @permission_checker(['resource.change_resource'])
    def mutate(root, info, data):
        try:
            instance = Resource.objects.get(id=data['id'], created_by=info.context.user)
        except Resource.DoesNotExist:
            return UpdateResource(errors=[
                dict(field='nonFieldErrors', messages=gettext('Resource does not exist.'))
            ])
        serializer = ResourceSerializer(instance=instance,
                                        data=data,
                                        context={'request': info.context},
                                        partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateResource(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateResource(result=instance, errors=None, ok=True)


class DeleteResource(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ResourceType)

    @staticmethod
    @permission_checker(['resource.delete_resource'])
    def mutate(root, info, id):
        try:
            instance = Resource.objects.get(id=id, created_by=info.context.user)
        except Resource.DoesNotExist:
            return UpdateResource(errors=[
                dict(field='nonFieldErrors', messages=gettext('Resource does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteResource(result=instance, errors=None, ok=True)


class ResourceGroupCreateInputType(graphene.InputObjectType):
    name = graphene.String(required=True)


class ResourceGroupUpdateInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    name = graphene.String()


class CreateResourceGroup(graphene.Mutation):
    class Arguments:
        data = ResourceGroupCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ResourceGroupType)

    @staticmethod
    @permission_checker(['resource.add_resource'])
    def mutate(root, info, data):
        serializer = ResourceGroupSerializer(data=data,
                                             context={'request': info.context})
        if errors := mutation_is_not_valid(serializer):
            return CreateResourceGroup(errors=errors, ok=False)
        instance = serializer.save()
        return CreateResourceGroup(result=instance, errors=None, ok=True)


class UpdateResourceGroup(graphene.Mutation):
    class Arguments:
        data = ResourceGroupUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ResourceGroupType)

    @staticmethod
    @permission_checker(['resource.change_resource'])
    def mutate(root, info, data):
        try:
            instance = ResourceGroup.objects.get(id=data['id'], created_by=info.context.user)
        except ResourceGroup.DoesNotExist:
            return UpdateResourceGroup(errors=[
                dict(field='nonFieldErrors', messages=gettext('ResourceGroup does not exist.'))
            ])
        serializer = ResourceGroupSerializer(instance=instance,
                                             data=data,
                                             context={'request': info.context},
                                             partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateResourceGroup(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateResourceGroup(result=instance, errors=None, ok=True)


class DeleteResourceGroup(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ResourceGroupType)

    @staticmethod
    @permission_checker(['resource.delete_resource'])
    def mutate(root, info, id):
        try:
            instance = ResourceGroup.objects.get(id=id, created_by=info.context.user)
        except ResourceGroup.DoesNotExist:
            return DeleteResourceGroup(errors=[
                dict(field='nonFieldErrors', messages=gettext('ResourceGroup does not exist.'))
            ])
        can_delete, msg = instance.can_delete()
        if not can_delete:
            return DeleteResourceGroup(errors=[
                dict(field='nonFieldErrors', messages=msg)
            ])
        instance.delete()
        instance.id = id
        return DeleteResourceGroup(result=instance, errors=None, ok=True)


class Mutation:
    create_resource = CreateResource.Field()
    update_resource = UpdateResource.Field()
    delete_resource = DeleteResource.Field()
    create_resource_group = CreateResourceGroup.Field()
    update_resource_group = UpdateResourceGroup.Field()
    delete_resource_group = DeleteResourceGroup.Field()
