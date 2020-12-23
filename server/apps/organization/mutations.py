import graphene
from django.utils.translation import gettext, gettext_lazy as _

from apps.contact.mutations import ContactWithoutOrganizationInputType
from apps.organization.models import Organization, OrganizationKind
from apps.organization.schema import OrganizationType, OrganizationKindObjectType
from apps.organization.serializers import OrganizationSerializer, OrganizationKindSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid


# organization kind
from utils.permissions import permission_checker


class OrganizationKindCreateInputType(graphene.InputObjectType):
    name = graphene.String(required=True)


class OrganizationKindUpdateInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    name = graphene.String(required=True)


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
            return UpdateOrganizationKind(errors=[
                dict(field='nonFieldErrors', messages=gettext('Organization type does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteOrganizationKind(result=instance, errors=None, ok=True)


# organization


class OrganizationCreateInputType(graphene.InputObjectType):
    name = graphene.String(required=True)
    short_name = graphene.String(required=True)
    organization_kind = graphene.ID(description="Foreign Key to OrganizationKindObjectType")
    methodology = graphene.String(required=True)
    breakdown = graphene.String(required=False)
    parent = graphene.ID(description="Foreign Key to self")
    contacts = graphene.List(graphene.NonNull(ContactWithoutOrganizationInputType))


class OrganizationUpdateInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    name = graphene.String()
    short_name = graphene.String()
    organization_kind = graphene.ID(description="Foreign Key to OrganizationKindObjectType")
    methodology = graphene.String()
    breakdown = graphene.String()
    parent = graphene.ID(description="Foreign Key to self")


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
            return UpdateOrganization(errors=[
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
