import graphene

from apps.contact.mutations import ContactInputType
from apps.organization.models import Organization
from apps.organization.schema import OrganizationType
from apps.organization.serializers import OrganizationSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid


class OrganizationCreateInputType(graphene.InputObjectType):
    title = graphene.String(required=True)
    short_name = graphene.String(required=True)
    organization_type = graphene.Int()
    methodology = graphene.String(required=True)
    source_detail_methodology = graphene.String(required=True)
    parent = graphene.Int()
    contacts = graphene.List(ContactInputType)


class OrganizationUpdateInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    title = graphene.String()
    short_name = graphene.String()
    organization_type = graphene.Int()
    methodology = graphene.String()
    source_detail_methodology = graphene.String()
    parent = graphene.Int()


class CreateOrganization(graphene.Mutation):
    class Arguments:
        organization = OrganizationCreateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    organization = graphene.Field(OrganizationType)

    @staticmethod
    def mutate(root, info, organization):
        serializer = OrganizationSerializer(data=organization)
        if errors := mutation_is_not_valid(serializer):
            return CreateOrganization(errors=errors, ok=False)
        instance = serializer.save()
        return CreateOrganization(organization=instance, errors=None, ok=True)


class UpdateOrganization(graphene.Mutation):
    class Arguments:
        organization = OrganizationUpdateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    organization = graphene.Field(OrganizationType)

    @staticmethod
    def mutate(root, info, organization):
        try:
            instance = Organization.objects.get(id=organization['id'])
        except Organization.DoesNotExist:
            return UpdateOrganization(errors=[
                CustomErrorType(field='non_field_errors', messages=['Organization Does Not Exist.'])
            ])
        serializer = OrganizationSerializer(instance=instance, data=organization, partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateOrganization(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateOrganization(organization=instance, errors=None, ok=True)


class DeleteOrganization(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    organization = graphene.Field(OrganizationType)

    @staticmethod
    def mutate(root, info, organization):
        try:
            instance = Organization.objects.get(id=organization['id'])
        except Organization.DoesNotExist:
            return UpdateOrganization(errors=[
                CustomErrorType(field='non_field_errors', messages=['Organization Does Not Exist.'])
            ])
        instance.delete()
        instance.id = organization['id']
        return DeleteOrganization(organization=instance, errors=None, ok=True)


class Mutation(object):
    create_organization = CreateOrganization.Field()
    update_organization = UpdateOrganization.Field()
    delete_organization = DeleteOrganization.Field()
