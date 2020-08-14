import graphene
from graphene_django_extras import DjangoObjectField, PageGraphqlPagination, \
    DjangoListObjectType, DjangoListObjectField, DjangoObjectType, DjangoFilterPaginateListField

from apps.contact.enums import CommunicationMediumGrapheneEnum, DesignationGrapheneEnum
from apps.contact.filters import ContactFilter
from apps.contact.models import Contact, Communication


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
    communications = DjangoFilterPaginateListField(CommunicationType,
                                                   pagination=PageGraphqlPagination(page_size_query_param='pageSize'))


class ContactListType(DjangoListObjectType):
    class Meta:
        model = Contact
        filterset_class = ContactFilter
        pagination = PageGraphqlPagination(page_size_query_param='pageSize')


class Query:
    contact = DjangoObjectField(ContactType)
    communication = DjangoObjectField(CommunicationType)
    contact_list = DjangoListObjectField(ContactListType)
    communication_list = DjangoListObjectField(CommunicationListType)
