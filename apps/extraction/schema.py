import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField
import logging

from apps.extraction.filters import EntryExtractionFilterSet, ExtractionQueryFilter
from apps.extraction.models import (
    ExtractionQuery,
)
from apps.entry.schema import EntryListType
from apps.entry.enums import (
    RoleGrapheneEnum,
    GenderTypeGrapheneEnum,
    DisplacementTypeGrapheneEnum,
    EntryReviewerGrapheneEnum,
)
from apps.crisis.enums import CrisisTypeGrapheneEnum
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.pagination import PageGraphqlPaginationWithoutCount

logger = logging.getLogger(__name__)


class ExtractionQueryObjectType(DjangoObjectType):
    class Meta:
        model = ExtractionQuery

    entries = DjangoPaginatedListObjectField(EntryListType,
                                             pagination=PageGraphqlPaginationWithoutCount(
                                                 page_size_query_param='pageSize'
                                             ), accessor='entries')
    filter_figure_roles = graphene.List(graphene.NonNull(RoleGrapheneEnum))
    filter_event_crisis_types = graphene.List(graphene.NonNull(CrisisTypeGrapheneEnum))
    filter_figure_sex_types = graphene.List(graphene.NonNull(GenderTypeGrapheneEnum))
    filter_figure_displacement_types = graphene.List(graphene.NonNull(DisplacementTypeGrapheneEnum))
    filter_entry_review_status = graphene.List(graphene.NonNull(EntryReviewerGrapheneEnum))


class ExtractionQueryListType(CustomDjangoListObjectType):
    class Meta:
        model = ExtractionQuery
        filterset_class = ExtractionQueryFilter


class Query:
    extraction_query = DjangoObjectField(ExtractionQueryObjectType)
    extraction_query_list = DjangoPaginatedListObjectField(ExtractionQueryListType,
                                                           pagination=PageGraphqlPaginationWithoutCount(
                                                               page_size_query_param='pageSize'
                                                           ))
    extraction_entry_list = DjangoPaginatedListObjectField(EntryListType,
                                                           pagination=PageGraphqlPaginationWithoutCount(
                                                               page_size_query_param='pageSize'
                                                           ),
                                                           filterset_class=EntryExtractionFilterSet)
