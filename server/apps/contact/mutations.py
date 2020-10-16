import graphene
from django.utils.translation import gettext_lazy as _

from apps.contact.enums import DesignationGrapheneEnum, CommunicationMediumGrapheneEnum, GenderGrapheneEnum
from apps.contact.models import Contact, Communication
from apps.contact.schema import ContactType, CommunicationType
from apps.contact.serializers import ContactSerializer, CommunicationSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker


class ContactInputType(object):
    designation = graphene.NonNull(DesignationGrapheneEnum)
    first_name = graphene.String(required=True)
    last_name = graphene.String(required=True)
    gender = graphene.NonNull(GenderGrapheneEnum)
    job_title = graphene.String(required=True)
    country = graphene.ID()
    countries_of_operation = graphene.List(graphene.ID)
    email = graphene.String()
    phone = graphene.String()
    comment = graphene.String()


class ContactWithoutOrganizationInputType(ContactInputType, graphene.InputObjectType):
    """
    Contact InputType without Organization
    """
    pass


class ContactCreateInputType(ContactInputType, graphene.InputObjectType):
    """
    Contact Create InputType
    """
    organization = graphene.ID(required=True)


class ContactUpdateInputType(graphene.InputObjectType):
    """
    Contact Update InputType
    """
    id = graphene.ID(required=True)
    designation = graphene.Field(DesignationGrapheneEnum)
    first_name = graphene.String()
    last_name = graphene.String()
    gender = graphene.Field(GenderGrapheneEnum)
    job_title = graphene.String()
    organization = graphene.ID()
    country = graphene.ID()
    countries_of_operation = graphene.List(graphene.ID)
    email = graphene.String()
    phone = graphene.String()
    comment = graphene.String()


class CreateContact(graphene.Mutation):
    class Arguments:
        contact = ContactCreateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    contact = graphene.Field(ContactType)

    @staticmethod
    @permission_checker(['contact.add_contact'])
    def mutate(root, info, contact):
        serializer = ContactSerializer(data=contact)
        if errors := mutation_is_not_valid(serializer):
            return CreateContact(errors=errors, ok=False)
        instance = serializer.save()
        return CreateContact(contact=instance, errors=None, ok=True)


class UpdateContact(graphene.Mutation):
    class Arguments:
        contact = ContactUpdateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    contact = graphene.Field(ContactType)

    @staticmethod
    @permission_checker(['contact.change_contact'])
    def mutate(root, info, contact):
        try:
            instance = Contact.objects.get(id=contact['id'])
        except Contact.DoesNotExist:
            return UpdateContact(errors=[
                CustomErrorType(field='non_field_errors', messages=[_('Contact does not exist.')])
            ])
        serializer = ContactSerializer(instance=instance, data=contact, partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateContact(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateContact(contact=instance, errors=None, ok=True)


class DeleteContact(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    contact = graphene.Field(ContactType)

    @staticmethod
    @permission_checker(['contact.delete_contact'])
    def mutate(root, info, id):
        try:
            instance = Contact.objects.get(id=id)
        except Contact.DoesNotExist:
            return UpdateContact(errors=[
                CustomErrorType(field='non_field_errors', messages=[_('Contact does not exist.')])
            ])
        instance.delete()
        instance.id = id
        return DeleteContact(contact=instance, errors=None, ok=True)


# Communication #


class CommunicationCreateInputType(graphene.InputObjectType):
    """
    Communication Create InputType
    """
    contact = graphene.ID(required=True)
    title = graphene.String()
    subject = graphene.String(required=True)
    content = graphene.String(required=True)
    date_time = graphene.DateTime()
    medium = graphene.NonNull(CommunicationMediumGrapheneEnum)


class CommunicationUpdateInputType(graphene.InputObjectType):
    """
    Communication Update InputType
    """
    contact = graphene.ID()
    country = graphene.ID()
    title = graphene.String()
    subject = graphene.String()
    content = graphene.String()
    date_time = graphene.DateTime()
    medium = graphene.Field(CommunicationMediumGrapheneEnum)


class CreateCommunication(graphene.Mutation):
    class Arguments:
        communication = CommunicationCreateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    communication = graphene.Field(CommunicationType)

    @staticmethod
    def mutate(root, info, communication):
        serializer = CommunicationSerializer(data=communication)
        if errors := mutation_is_not_valid(serializer):
            return CreateCommunication(errors=errors, ok=False)
        instance = serializer.save()
        return CreateCommunication(communication=instance, errors=None, ok=True)


class UpdateCommunication(graphene.Mutation):
    class Arguments:
        communication = CommunicationUpdateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    communication = graphene.Field(CommunicationType)

    @staticmethod
    def mutate(root, info, communication):
        try:
            instance = Communication.objects.get(id=communication['id'])
        except Communication.DoesNotExist:
            return UpdateCommunication(errors=[
                CustomErrorType(field='non_field_errors', messages=[_('Communication does not exist.')])
            ])
        serializer = CommunicationSerializer(instance=instance, data=communication, partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateCommunication(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateCommunication(communication=instance, errors=None, ok=True)


class DeleteCommunication(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    communication = graphene.Field(CommunicationType)

    @staticmethod
    def mutate(root, info, id):
        try:
            instance = Communication.objects.get(id=id)
        except Communication.DoesNotExist:
            return DeleteCommunication(errors=[
                CustomErrorType(field='non_field_errors', messages=[_('Communication does not exist.')])
            ])
        instance.delete()
        instance.id = id
        return DeleteCommunication(communication=instance, errors=None, ok=True)


class Mutation(object):
    create_contact = CreateContact.Field()
    update_contact = UpdateContact.Field()
    delete_contact = DeleteContact.Field()
    create_communication = CreateCommunication.Field()
    update_communication = UpdateCommunication.Field()
    delete_communication = DeleteCommunication.Field()
