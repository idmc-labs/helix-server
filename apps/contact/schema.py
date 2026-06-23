import graphene
from graphene_django_extras import DjangoObjectField

from apps.contact.enums import DesignationGrapheneEnum
from apps.contact.filters import CommunicationFilter, CommunicationMediumFilter, ContactFilter
from apps.contact.models import Communication, CommunicationMedium, Contact
from apps.entry.enums import GenderTypeGrapheneEnum
from utils.graphene.enums import EnumDescription
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.pagination import PageGraphqlPaginationWithoutCount
from utils.graphene.relation_loaders import RelationBatchedDjangoObjectType
from utils.graphene.types import CustomDjangoListObjectType


class CommunicationMediumType(RelationBatchedDjangoObjectType):
    class Meta:
        model = CommunicationMedium
        filter_fields = []


class CommunicationMediumListType(CustomDjangoListObjectType):
    class Meta:
        model = CommunicationMedium
        filterset_class = CommunicationMediumFilter


class CommunicationType(RelationBatchedDjangoObjectType):
    class Meta:
        model = Communication


class CommunicationListType(CustomDjangoListObjectType):
    class Meta:
        model = Communication
        filterset_class = CommunicationFilter


class ContactType(RelationBatchedDjangoObjectType):
    class Meta:
        model = Contact

    full_name = graphene.Field(graphene.String)
    designation = graphene.Field(DesignationGrapheneEnum)
    designation_display = EnumDescription(source="get_designation_display")
    gender = graphene.Field(GenderTypeGrapheneEnum)
    gender_display = EnumDescription(source="get_gender_display")
    communications = DjangoPaginatedListObjectField(
        CommunicationListType,
        pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize"),
        related_name="communications",
    )


class ContactListType(CustomDjangoListObjectType):
    class Meta:
        model = Contact
        filterset_class = ContactFilter


class Query:
    contact = DjangoObjectField(ContactType)
    communication = DjangoObjectField(CommunicationType)
    contact_list = DjangoPaginatedListObjectField(
        ContactListType, pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize")
    )
    communication_medium_list = DjangoPaginatedListObjectField(CommunicationMediumListType)
    communication_list = DjangoPaginatedListObjectField(
        CommunicationListType, pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize")
    )
