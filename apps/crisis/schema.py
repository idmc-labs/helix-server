import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField
from utils.graphene.enums import EnumDescription

from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.crisis.filters import CrisisFilter
from apps.crisis.models import Crisis
from apps.contrib.commons import DateAccuracyGrapheneEnum
from apps.event.schema import EventListType
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.pagination import PageGraphqlPaginationWithoutCount


class CrisisReviewCountType(graphene.ObjectType):
    review_not_started_count = graphene.Int(required=False)
    review_in_progress_count = graphene.Int(required=False)
    review_re_request_count = graphene.Int(required=False)
    review_approved_count = graphene.Int(required=False)
    total_count = graphene.Int(required=False)
    progress = graphene.Float(required=False)


class CrisisType(DjangoObjectType):
    class Meta:
        model = Crisis

    crisis_type = graphene.Field(CrisisTypeGrapheneEnum)
    crisis_type_display = EnumDescription(source='get_crisis_type_display')
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
    start_date_accuracy_display = EnumDescription(source='get_start_date_accuracy_display')
    end_date_accuracy = graphene.Field(DateAccuracyGrapheneEnum)
    end_date_accuracy_display = EnumDescription(source='get_end_date_accuracy_display')
    event_count = graphene.Field(graphene.Int)
    review_count = graphene.Field(CrisisReviewCountType)

    def resolve_total_stock_idp_figures(root, info, **kwargs):
        NULL = 'null'
        value = getattr(
            root,
            Crisis.IDP_FIGURES_ANNOTATE,
            NULL
        )
        if value != NULL:
            return value
        return info.context.crisis_crisis_total_stock_idp_figures.load(root.id)

    def resolve_total_flow_nd_figures(root, info, **kwargs):
        NULL = 'null'
        value = getattr(
            root,
            Crisis.ND_FIGURES_ANNOTATE,
            NULL,
        )
        if value != NULL:
            return value
        return info.context.crisis_crisis_total_flow_nd_figures.load(root.id)

    def resolve_event_count(root, info, **kwargs):
        return info.context.event_count_dataloader.load(root.id)

    def resolve_review_count(root, info, **kwargs):
        return info.context.crisis_review_count_dataloader.load(root.id)


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
