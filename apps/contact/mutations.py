from django.utils.translation import gettext
import graphene

from apps.contact.models import Contact, Communication
from apps.contact.schema import ContactType, CommunicationType
from apps.contact.serializers import (
    ContactSerializer,
    CommunicationSerializer,
    ContactUpdateSerializer,
    CommunicationUpdateSerializer,
)
from utils.mutation import generate_input_type_for_serializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker


ContactCreateInputType = generate_input_type_for_serializer(
    'ContactCreateInputType',
    ContactSerializer
)


ContactUpdateInputType = generate_input_type_for_serializer(
    'ContactUpdateInputType',
    ContactUpdateSerializer
)


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
                dict(field='nonFieldErrors', messages=gettext('Contact does not exist.'))
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
                dict(field='nonFieldErrors', messages=gettext('Contact does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteContact(result=instance, errors=None, ok=True)


# Communication #

CommunicationCreateInputType = generate_input_type_for_serializer(
    'CommunicationCreateInputType',
    CommunicationSerializer
)

CommunicationUpdateInputType = generate_input_type_for_serializer(
    'CommunicationUpdateInputType',
    CommunicationUpdateSerializer
)


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
                dict(field='nonFieldErrors', messages=gettext('Communication does not exist.'))
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
                dict(field='nonFieldErrors', messages=gettext('Communication does not exist.'))
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
