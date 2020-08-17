import graphene
from graphene_django.rest_framework.mutation import SerializerMutation

from apps.contact.enums import DesignationGrapheneEnum, CommunicationMediumGrapheneEnum, GenderGrapheneEnum
from apps.contact.models import Contact, Communication
from apps.contact.schema import ContactType, CommunicationType
from apps.contact.serializers import ContactSerializer, CommunicationSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid


class ContactInputType(graphene.InputObjectType):
    """
    Contact InputType without Organization
    """
    designation = graphene.NonNull(DesignationGrapheneEnum)
    first_name = graphene.String(required=True)
    last_name = graphene.String(required=True)
    gender = graphene.NonNull(GenderGrapheneEnum)
    job_title = graphene.String(required=True)
    country = graphene.Int()
    countries_of_operation = graphene.List(graphene.Int)
    email = graphene.String()
    phone = graphene.String()
    comment = graphene.String()


class ContactCreateInputType(graphene.InputObjectType):
    """
    Contact Create InputType
    """
    designation = graphene.NonNull(DesignationGrapheneEnum)
    first_name = graphene.String(required=True)
    last_name = graphene.String(required=True)
    gender = graphene.NonNull(GenderGrapheneEnum)
    job_title = graphene.String(required=True)
    organization = graphene.Int(required=True)
    country = graphene.Int()
    countries_of_operation = graphene.List(graphene.Int)
    email = graphene.String()
    phone = graphene.String()
    comment = graphene.String()


class ContactUpdateInputType(graphene.InputObjectType):
    """
    Contact Update InputType
    """
    id = graphene.Int(required=True)
    designation = graphene.Field(DesignationGrapheneEnum)
    first_name = graphene.String()
    last_name = graphene.String()
    gender = graphene.Field(GenderGrapheneEnum)
    job_title = graphene.String()
    organization = graphene.Int()
    country = graphene.Int()
    countries_of_operation = graphene.List(graphene.Int)
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
    def mutate(root, info, contact):
        try:
            instance = Contact.objects.get(id=contact['id'])
        except Contact.DoesNotExist:
            return UpdateContact(errors=[
                CustomErrorType(field='non_field_errors', messages=['Contact Does Not Exist.'])
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
    def mutate(root, info, contact):
        try:
            instance = Contact.objects.get(id=contact['id'])
        except Contact.DoesNotExist:
            return UpdateContact(errors=[
                CustomErrorType(field='non_field_errors', messages=['Contact Does Not Exist.'])
            ])
        instance.delete()
        instance.id = contact['id']
        return DeleteContact(contact=instance, errors=None, ok=True)


# Communication #


class CommunicationCreateInputType(graphene.InputObjectType):
    """
    Communication Create InputType
    """
    contact = graphene.Int(required=True)
    country = graphene.Int()
    subject = graphene.String(required=True)
    content = graphene.String(required=True)
    date = graphene.Date()
    medium = graphene.NonNull(CommunicationMediumGrapheneEnum)


class CommunicationUpdateInputType(graphene.InputObjectType):
    """
    Communication Update InputType
    """
    contact = graphene.Int()
    country = graphene.Int()
    subject = graphene.String()
    content = graphene.String()
    date = graphene.Date()
    medium = graphene.NonNull(CommunicationMediumGrapheneEnum)


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
                CustomErrorType(field='non_field_errors', messages=['Communication Does Not Exist.'])
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
    def mutate(root, info, communication):
        try:
            instance = Communication.objects.get(id=communication['id'])
        except Communication.DoesNotExist:
            return DeleteCommunication(errors=[
                CustomErrorType(field='non_field_errors', messages=['Communication Does Not Exist.'])
            ])
        instance.delete()
        instance.id = communication['id']
        return DeleteCommunication(communication=instance, errors=None, ok=True)


class Mutation(object):
    create_contact = CreateContact.Field()
    update_contact = UpdateContact.Field()
    delete_contact = DeleteContact.Field()
    create_communication = CreateCommunication.Field()
    update_communication = UpdateCommunication.Field()
    delete_communication = DeleteCommunication.Field()
