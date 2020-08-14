from graphene_django_extras import DjangoSerializerMutation

from apps.contact.customs import CustomDjangoSerializerMutation
from apps.contact.serializers import ContactSerializer, CommunicationSerializer, CommunicationNestedSerializer


class CommunicationNestedMutation(DjangoSerializerMutation):
    class Meta:
        serializer_class = CommunicationNestedSerializer
        include_fields = ['country', 'subject', 'content', 'date', 'medium']
        description = "Nested Communication Mutation For Contact"


class ContactMutation(CustomDjangoSerializerMutation):
    class Meta:
        serializer_class = ContactSerializer
        nested_fields = {
            'communications': CommunicationNestedSerializer
        }


class CommunicationMutation(DjangoSerializerMutation):
    class Meta:
        serializer_class = CommunicationSerializer


class Mutation(object):
    create_contact = ContactMutation.CreateField()
    create_communication = CommunicationMutation.CreateField()
