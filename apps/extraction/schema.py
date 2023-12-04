import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField
import logging

from apps.extraction.filters import ExtractionQueryFilter
from apps.extraction.models import (
    ExtractionQuery,
)
from apps.entry.schema import EntryListType

from apps.entry.enums import (
    RoleGrapheneEnum,
    FigureCategoryTypeEnum,
    FigureTermsEnum,
    FigureReviewStatusEnum,
)
from apps.crisis.enums import CrisisTypeGrapheneEnum
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.pagination import PageGraphqlPaginationWithoutCount

logger = logging.getLogger(__name__)


class ExtractionQueryObjectType(DjangoObjectType):
    class Meta:
        model = ExtractionQuery

    entries = DjangoPaginatedListObjectField(EntryListType,
                                             pagination=PageGraphqlPaginationWithoutCount(
                                                 page_size_query_param='pageSize'
                                             ), accessor='entries')
    filter_figure_roles = graphene.List(graphene.NonNull(RoleGrapheneEnum))
    filter_figure_crisis_types = graphene.List(graphene.NonNull(CrisisTypeGrapheneEnum))
    filter_figure_categories = graphene.List(graphene.NonNull(FigureCategoryTypeEnum))
    filter_figure_terms = graphene.List(graphene.NonNull(FigureTermsEnum))
    filter_figure_review_status = graphene.List(graphene.NonNull(FigureReviewStatusEnum))


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
