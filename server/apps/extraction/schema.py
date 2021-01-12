import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField, PageGraphqlPagination
import logging

from apps.extraction.filters import EntryExtractionFilterSet
from apps.extraction.models import (
    ExtractionQuery,
)
from apps.entry.schema import EntryListType
from apps.entry.enums import RoleGrapheneEnum
from utils.fields import (
    DjangoPaginatedListObjectField,
    CustomDjangoListObjectType,
)

logger = logging.getLogger(__name__)


class ExtractionQueryObjectType(DjangoObjectType):
    class Meta:
        model = ExtractionQuery

    entries = DjangoPaginatedListObjectField(EntryListType,
                                             pagination=PageGraphqlPagination(
                                                 page_size_query_param='pageSize'
                                             ), accessor='entries')
    figure_roles = graphene.List(graphene.NonNull(RoleGrapheneEnum))


class ExtractionQueryListType(CustomDjangoListObjectType):
    class Meta:
        model = ExtractionQuery
        filter_fields = {
            'id': ('exact',),
        }


class Query:
    extraction_query = DjangoObjectField(ExtractionQueryObjectType)
    extraction_query_list = DjangoPaginatedListObjectField(ExtractionQueryListType)
    extraction_entry_list = DjangoPaginatedListObjectField(EntryListType,
                                                           pagination=PageGraphqlPagination(
                                                               page_size_query_param='pageSize'
                                                           ),
                                                           filterset_class=EntryExtractionFilterSet)
