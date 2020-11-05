from django.utils.translation import gettext
import graphene
from graphene_file_upload.scalars import Upload

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
    countries_of_operation = graphene.List(graphene.NonNull(graphene.ID))
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
    countries_of_operation = graphene.List(graphene.NonNull(graphene.ID))
    email = graphene.String()
    phone = graphene.String()
    comment = graphene.String()


class CreateContact(graphene.Mutation):
    class Arguments:
        data = ContactCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ContactType)

    @staticmethod
    @permission_checker(['contact.add_contact'])
    def mutate(root, info, data):
        serializer = ContactSerializer(data=data)
        if errors := mutation_is_not_valid(serializer):
            return CreateContact(errors=errors, ok=False)
        instance = serializer.save()
        return CreateContact(result=instance, errors=None, ok=True)


class UpdateContact(graphene.Mutation):
    class Arguments:
        data = ContactUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ContactType)

    @staticmethod
    @permission_checker(['contact.change_contact'])
    def mutate(root, info, data):
        try:
            instance = Contact.objects.get(id=data['id'])
        except Contact.DoesNotExist:
            return UpdateContact(errors=[
                CustomErrorType(field='non_field_errors', messages=gettext('Contact does not exist.'))
            ])
        serializer = ContactSerializer(instance=instance, data=data, partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateContact(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateContact(result=instance, errors=None, ok=True)


class DeleteContact(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ContactType)

    @staticmethod
    @permission_checker(['contact.delete_contact'])
    def mutate(root, info, id):
        try:
            instance = Contact.objects.get(id=id)
        except Contact.DoesNotExist:
            return UpdateContact(errors=[
                CustomErrorType(field='non_field_errors', messages=gettext('Contact does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteContact(result=instance, errors=None, ok=True)


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
    attachment = Upload(required=False)


class CommunicationUpdateInputType(graphene.InputObjectType):
    """
    Communication Update InputType
    """
    id = graphene.ID(required=True)
    contact = graphene.ID()
    country = graphene.ID()
    title = graphene.String()
    subject = graphene.String()
    content = graphene.String()
    date_time = graphene.DateTime()
    medium = graphene.Field(CommunicationMediumGrapheneEnum)
    attachment = Upload(required=False)


class CreateCommunication(graphene.Mutation):
    class Arguments:
        data = CommunicationCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(CommunicationType)

    @staticmethod
    def mutate(root, info, data):
        serializer = CommunicationSerializer(data=data)
        if errors := mutation_is_not_valid(serializer):
            return CreateCommunication(errors=errors, ok=False)
        instance = serializer.save()
        return CreateCommunication(result=instance, errors=None, ok=True)


class UpdateCommunication(graphene.Mutation):
    class Arguments:
        data = CommunicationUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(CommunicationType)

    @staticmethod
    def mutate(root, info, data):
        try:
            instance = Communication.objects.get(id=data['id'])
        except Communication.DoesNotExist:
            return UpdateCommunication(errors=[
                CustomErrorType(field='non_field_errors', messages=gettext('Communication does not exist.'))
            ])
        serializer = CommunicationSerializer(instance=instance, data=data, partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateCommunication(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateCommunication(result=instance, errors=None, ok=True)


class DeleteCommunication(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(CommunicationType)

    @staticmethod
    def mutate(root, info, id):
        try:
            instance = Communication.objects.get(id=id)
        except Communication.DoesNotExist:
            return DeleteCommunication(errors=[
                CustomErrorType(field='non_field_errors', messages=gettext('Communication does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteCommunication(result=instance, errors=None, ok=True)


class Mutation(object):
    create_contact = CreateContact.Field()
    update_contact = UpdateContact.Field()
    delete_contact = DeleteContact.Field()
    create_communication = CreateCommunication.Field()
    update_communication = UpdateCommunication.Field()
    delete_communication = DeleteCommunication.Field()
