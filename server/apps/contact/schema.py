import graphene
from graphene import Field
from graphene_django import DjangoObjectType

from apps.contact.models import Contact, Communication


class ContactType(DjangoObjectType):
    class Meta:
        model = Contact


class CommunicationType(DjangoObjectType):
    class Meta:
        model = Communication


class Query:
    contact = Field(ContactType, id=graphene.Int())
    # contacts =
    communication = Field(CommunicationType, id=graphene.Int())
