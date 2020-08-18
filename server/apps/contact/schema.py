import graphene
from graphene_django_extras import DjangoObjectField, PageGraphqlPagination, \
    DjangoObjectType

from apps.contact.enums import CommunicationMediumGrapheneEnum, DesignationGrapheneEnum, GenderGrapheneEnum
from apps.contact.filters import ContactFilter
from apps.contact.models import Contact, Communication
from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType


class CommunicationType(DjangoObjectType):
    class Meta:
        model = Communication
        filter_fields = []

    medium = graphene.Field(CommunicationMediumGrapheneEnum)


class CommunicationListType(CustomDjangoListObjectType):
    class Meta:
        model = Communication
        filter_fields = {
            'contact': ['exact'],
            'subject': ['icontains']
        }


class ContactType(DjangoObjectType):
    class Meta:
        model = Contact

    designation = graphene.Field(DesignationGrapheneEnum)
    gender = graphene.Field(GenderGrapheneEnum)
    communications = DjangoPaginatedListObjectField(CommunicationListType,
                                                    pagination=PageGraphqlPagination(
                                                        page_size_query_param='pageSize'
                                                    ))


class ContactListType(CustomDjangoListObjectType):
    class Meta:
        model = Contact
        filterset_class = ContactFilter


class Query:
    contact = DjangoObjectField(ContactType)
    communication = DjangoObjectField(CommunicationType)
    contact_list = DjangoPaginatedListObjectField(ContactListType,
                                                  pagination=PageGraphqlPagination(
                                                      page_size_query_param='pageSize'
                                                  ))
    communication_list = DjangoPaginatedListObjectField(CommunicationListType,
                                                        pagination=PageGraphqlPagination(
                                                            page_size_query_param='pageSize'
                                                        ))
