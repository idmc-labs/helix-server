import graphene
from graphene_django_extras import DjangoSerializerMutation

from apps.contact.serializers import ContactSerializer


class ContactMutation(DjangoSerializerMutation):
    class Meta:
        serializer_class = ContactSerializer


class Mutation:
    create_contact, delete_contact, update_contact = ContactMutation.MutationFields()
