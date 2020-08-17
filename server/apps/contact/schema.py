import graphene
from graphene_django_extras import DjangoObjectField, PageGraphqlPagination, \
    DjangoListObjectType, DjangoObjectType, DjangoFilterPaginateListField

from apps.contact.enums import CommunicationMediumGrapheneEnum, DesignationGrapheneEnum, GenderGrapheneEnum
from apps.contact.filters import ContactFilter
from apps.contact.models import Contact, Communication
from utils.fields import DjangoPaginatedListObjectField


class CommunicationType(DjangoObjectType):
    class Meta:
        model = Communication
        filter_fields = []

    medium = graphene.Field(CommunicationMediumGrapheneEnum)


class CommunicationListType(DjangoListObjectType):
    class Meta:
        model = Communication
        filter_fields = {
            'contact': ['exact'],
            'subject': ['icontains']
        }
        pagination = PageGraphqlPagination(page_size_query_param='pageSize')


class ContactType(DjangoObjectType):
    class Meta:
        model = Contact

    designation = graphene.Field(DesignationGrapheneEnum)
    gender = graphene.Field(GenderGrapheneEnum)
    communications = DjangoPaginatedListObjectField(CommunicationListType)


class ContactListType(DjangoListObjectType):
    class Meta:
        model = Contact
        filterset_class = ContactFilter
        pagination = PageGraphqlPagination(page_size_query_param='pageSize')


class Query:
    contact = DjangoObjectField(ContactType)
    communication = DjangoObjectField(CommunicationType)
    contact_list = DjangoPaginatedListObjectField(ContactListType)
    communication_list = DjangoPaginatedListObjectField(CommunicationListType)
