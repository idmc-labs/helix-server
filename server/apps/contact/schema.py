import graphene
from graphene import Field
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField, DjangoFilterPaginateListField, PageGraphqlPagination, \
    DjangoListObjectType, DjangoListObjectField

from apps.contact.models import Contact, Communication


class ContactType(DjangoObjectType):
    class Meta:
        model = Contact


class CommunicationType(DjangoObjectType):
    class Meta:
        model = Communication


class ContactListType(DjangoListObjectType):
    class Meta:
        model = Contact
        filter_fields = {
            "id": ("exact",),
            "name": ("icontains",),
        }
        pagination = PageGraphqlPagination(page_size_query_param='pageSize')


class Query:
    contact = DjangoObjectField(ContactType)
    contacts = DjangoListObjectField(ContactListType)
    communication = Field(CommunicationType, id=graphene.Int())
