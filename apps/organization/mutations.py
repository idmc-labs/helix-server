import graphene
from django.utils.translation import gettext

from apps.organization.models import Organization, OrganizationKind
from apps.organization.schema import OrganizationType, OrganizationKindObjectType
from apps.organization.serializers import (
    OrganizationSerializer,
    OrganizationUpdateSerializer,
    OrganizationKindSerializer,
    OrganizationKindUpdateSerializer,
)
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker
from utils.mutation import generate_input_type_for_serializer


# organization kind

OrganizationKindCreateInputType = generate_input_type_for_serializer(
    'OrganizationKindCreateInputType',
    OrganizationKindSerializer
)

OrganizationKindUpdateInputType = generate_input_type_for_serializer(
    'OrganizationKindUpdateInputType',
    OrganizationKindUpdateSerializer
)


class CreateOrganizationKind(graphene.Mutation):
    class Arguments:
        data = OrganizationKindCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(OrganizationKindObjectType)

    @staticmethod
    @permission_checker(['organization.add_organizationkind'])
    def mutate(root, info, data):
        serializer = OrganizationKindSerializer(data=data)
        if errors := mutation_is_not_valid(serializer):
            return CreateOrganizationKind(errors=errors, ok=False)
        instance = serializer.save()
        return CreateOrganizationKind(result=instance, errors=None, ok=True)


class UpdateOrganizationKind(graphene.Mutation):
    class Arguments:
        data = OrganizationKindUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(OrganizationKindObjectType)

    @staticmethod
    @permission_checker(['organization.change_organizationkind'])
    def mutate(root, info, data):
        try:
            instance = OrganizationKind.objects.get(id=data['id'])
        except OrganizationKind.DoesNotExist:
            return UpdateOrganizationKind(errors=[
                dict(field='nonFieldErrors', messages=gettext('Organization type does not exist.'))
            ])
        serializer = OrganizationKindSerializer(instance=instance, data=data, partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateOrganizationKind(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateOrganizationKind(result=instance, errors=None, ok=True)


class DeleteOrganizationKind(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(OrganizationKindObjectType)

    @staticmethod
    @permission_checker(['organization.delete_organizationkind'])
    def mutate(root, info, id):
        try:
            instance = OrganizationKind.objects.get(id=id)
        except OrganizationKind.DoesNotExist:
            return DeleteOrganizationKind(errors=[
                dict(field='nonFieldErrors', messages=gettext('Organization type does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteOrganizationKind(result=instance, errors=None, ok=True)


# organization


OrganizationCreateInputType = generate_input_type_for_serializer(
    'OrganizationCreateInputType',
    OrganizationSerializer
)

OrganizationUpdateInputType = generate_input_type_for_serializer(
    'OrganizationUpdateInputType',
    OrganizationUpdateSerializer
)


class CreateOrganization(graphene.Mutation):
    class Arguments:
        data = OrganizationCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(OrganizationType)

    @staticmethod
    @permission_checker(['organization.add_organization'])
    def mutate(root, info, data):
        serializer = OrganizationSerializer(data=data)
        if errors := mutation_is_not_valid(serializer):
            return CreateOrganization(errors=errors, ok=False)
        instance = serializer.save()
        return CreateOrganization(result=instance, errors=None, ok=True)


class UpdateOrganization(graphene.Mutation):
    class Arguments:
        data = OrganizationUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(OrganizationType)

    @staticmethod
    @permission_checker(['organization.change_organization'])
    def mutate(root, info, data):
        try:
            instance = Organization.objects.get(id=data['id'])
        except Organization.DoesNotExist:
            return UpdateOrganization(errors=[
                dict(field='nonFieldErrors', messages=gettext('Organization does not exist.'))
            ])
        serializer = OrganizationSerializer(instance=instance, data=data, partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateOrganization(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateOrganization(result=instance, errors=None, ok=True)


class DeleteOrganization(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(OrganizationType)

    @staticmethod
    @permission_checker(['organization.delete_organization'])
    def mutate(root, info, id):
        try:
            instance = Organization.objects.get(id=id)
        except Organization.DoesNotExist:
            return DeleteOrganization(errors=[
                dict(field='nonFieldErrors', messages=gettext('Organization does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteOrganization(result=instance, errors=None, ok=True)


class Mutation(object):
    create_organization = CreateOrganization.Field()
    update_organization = UpdateOrganization.Field()
    delete_organization = DeleteOrganization.Field()
    create_organization_kind = CreateOrganizationKind.Field()
    update_organization_kind = UpdateOrganizationKind.Field()
    delete_organization_kind = DeleteOrganizationKind.Field()
