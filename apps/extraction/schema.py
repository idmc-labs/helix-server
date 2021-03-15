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
from apps.crisis.enums import CrisisTypeGrapheneEnum
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField

logger = logging.getLogger(__name__)


class ExtractionQueryObjectType(DjangoObjectType):
    class Meta:
        model = ExtractionQuery

    entries = DjangoPaginatedListObjectField(EntryListType,
                                             pagination=PageGraphqlPagination(
                                                 page_size_query_param='pageSize'
                                             ), accessor='entries')
    filter_figure_roles = graphene.List(graphene.NonNull(RoleGrapheneEnum))
    filter_event_crisis_types = graphene.List(graphene.NonNull(CrisisTypeGrapheneEnum))


class ExtractionQueryListType(CustomDjangoListObjectType):
    class Meta:
        model = ExtractionQuery
        filter_fields = {
            'id': ('exact',),
            'name': ('icontains',),
        }


class Query:
    extraction_query = DjangoObjectField(ExtractionQueryObjectType)
    extraction_query_list = DjangoPaginatedListObjectField(ExtractionQueryListType,
                                                           pagination=PageGraphqlPagination(
                                                               page_size_query_param='pageSize'
                                                           ))
    extraction_entry_list = DjangoPaginatedListObjectField(EntryListType,
                                                           pagination=PageGraphqlPagination(
                                                               page_size_query_param='pageSize'
                                                           ),
                                                           filterset_class=EntryExtractionFilterSet)
