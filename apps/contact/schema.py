import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField

from apps.users.roles import USER_ROLE
from apps.contact.enums import DesignationGrapheneEnum
from apps.entry.enums import GenderTypeGrapheneEnum
from apps.contact.filters import ContactFilter, CommunicationFilter
from apps.contact.models import Contact, Communication, CommunicationMedium
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.pagination import PageGraphqlPaginationWithoutCount



class CommunicationMediumType(DjangoObjectType):
    class Meta:
        model = CommunicationMedium
        filter_fields = []


class CommunicationMediumListType(CustomDjangoListObjectType):
    class Meta:
        model = CommunicationMedium
        filter_fields = []

    @staticmethod
    def get_queryset(queryset, info):
        return communication_media_qs(info)


class CommunicationType(DjangoObjectType):
    class Meta:
        model = Communication


class CommunicationListType(CustomDjangoListObjectType):
    class Meta:
        model = Communication
        filterset_class = CommunicationFilter

    @staticmethod
    def get_queryset(queryset, info):
        return communication_qs(info)


class ContactType(DjangoObjectType):
    class Meta:
        model = Contact

    full_name = graphene.Field(graphene.String)
    designation = graphene.Field(DesignationGrapheneEnum)
    gender = graphene.Field(GenderTypeGrapheneEnum)
    communications = DjangoPaginatedListObjectField(
        CommunicationListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
        related_name='communications'
    )


class ContactListType(CustomDjangoListObjectType):
    class Meta:
        model = Contact
        filterset_class = ContactFilter

    @staticmethod
    def get_queryset(queryset, info):
        return contact_qs(info)


class Query:
    contact = DjangoObjectField(ContactType)
    communication = DjangoObjectField(CommunicationType)
    contact_list = DjangoPaginatedListObjectField(ContactListType,
                                                  pagination=PageGraphqlPaginationWithoutCount(
                                                      page_size_query_param='pageSize'
                                                  ))
    communication_medium_list = DjangoPaginatedListObjectField(CommunicationMediumListType)
    communication_list = DjangoPaginatedListObjectField(CommunicationListType,
                                                        pagination=PageGraphqlPaginationWithoutCount(
                                                            page_size_query_param='pageSize'
                                                        ))
