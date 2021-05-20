import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField

from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.crisis.filters import CrisisFilter
from apps.crisis.models import Crisis
from apps.contrib.commons import DateAccuracyGrapheneEnum
from apps.event.schema import EventListType
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.pagination import PageGraphqlPaginationWithoutCount


class CrisisReviewCountType(graphene.ObjectType):
    under_review_count = graphene.Int(required=False)
    signed_off_count = graphene.Int(required=False)
    review_complete_count = graphene.Int(required=False)
    to_be_reviewed_count = graphene.Int(required=False)


class CrisisType(DjangoObjectType):
    class Meta:
        model = Crisis

    crisis_type = graphene.Field(CrisisTypeGrapheneEnum)
    events = DjangoPaginatedListObjectField(
        EventListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
        related_name='events',
        reverse_related_name='crisis',
    )
    total_stock_idp_figures = graphene.Field(graphene.Int)
    total_flow_nd_figures = graphene.Field(graphene.Int)
    start_date_accuracy = graphene.Field(DateAccuracyGrapheneEnum)
    end_date_accuracy = graphene.Field(DateAccuracyGrapheneEnum)
    review_count = graphene.Field(CrisisReviewCountType)

    def resolve_review_count(root, info, **kwargs):
        return info.context.crisis_crisis_review_count_dataloader.load(root.id)

    def resolve_total_stock_idp_figures(root, info, **kwargs):
        value = getattr(
            root,
            Crisis.IDP_FIGURES_ANNOTATE,
            'null'
        )
        if value != 'null':
            return value
        return info.context.crisis_crisis_total_stock_idp_figures.load(root.id)

    def resolve_total_flow_nd_figures(root, info, **kwargs):
        value = getattr(
            root,
            Crisis.ND_FIGURES_ANNOTATE,
            'null',
        )
        if value != 'null':
            return value
        return info.context.crisis_crisis_total_flow_nd_figures.load(root.id)


class CrisisListType(CustomDjangoListObjectType):
    class Meta:
        model = Crisis
        filterset_class = CrisisFilter


class Query:
    crisis = DjangoObjectField(CrisisType)
    crisis_list = DjangoPaginatedListObjectField(CrisisListType,
                                                 pagination=PageGraphqlPaginationWithoutCount(
                                                     page_size_query_param='pageSize'
                                                 ))
