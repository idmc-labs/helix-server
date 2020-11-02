import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField, PageGraphqlPagination

from apps.contact.enums import DesignationGrapheneEnum, GenderGrapheneEnum
from apps.contact.filters import ContactFilter
from apps.contact.models import Contact, Communication, CommunicationMedium
from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType


class CommunicationMediumType(DjangoObjectType):
    class Meta:
        model = CommunicationMedium
        filter_fields = []


class CommunicationMediumListType(CustomDjangoListObjectType):
    class Meta:
        model = CommunicationMedium
        filter_fields = []


class CommunicationType(DjangoObjectType):
    class Meta:
        model = Communication


class CommunicationListType(CustomDjangoListObjectType):
    class Meta:
        model = Communication
        filter_fields = []


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
    communication_medium_list = DjangoPaginatedListObjectField(CommunicationMediumListType)
    communication_list = DjangoPaginatedListObjectField(CommunicationListType,
                                                        pagination=PageGraphqlPagination(
                                                            page_size_query_param='pageSize'
                                                        ))

