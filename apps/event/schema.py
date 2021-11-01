import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField

from apps.contrib.commons import DateAccuracyGrapheneEnum
from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.event.enums import EventOtherSubTypeEnum, QaRecommendedFigureEnum
from apps.event.models import (
    Event,
    Trigger,
    TriggerSubType,
    Violence,
    ViolenceSubType,
    Actor,
    DisasterSubCategory,
    DisasterCategory,
    DisasterSubType,
    DisasterType,
    OsvSubType,
)
from apps.event.filters import ActorFilter, EventFilter
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.pagination import PageGraphqlPaginationWithoutCount


class TriggerSubObjectType(DjangoObjectType):
    class Meta:
        model = TriggerSubType
        exclude_fields = ('events',)
        filter_fields = {}


class TriggerSubObjectListType(CustomDjangoListObjectType):
    class Meta:
        model = TriggerSubType
        filter_fields = {
            'name': ['unaccent__icontains']
        }


class TriggerType(DjangoObjectType):
    class Meta:
        model = Trigger
        exclude_fields = ('events',)


class TriggerListType(CustomDjangoListObjectType):
    class Meta:
        model = Trigger
        filter_fields = {
            'name': ['unaccent__icontains']
        }


class ViolenceSubObjectType(DjangoObjectType):
    class Meta:
        model = ViolenceSubType
        exclude_fields = ('events', 'violence')


class ViolenceSubObjectListType(CustomDjangoListObjectType):
    class Meta:
        model = ViolenceSubType
        filter_fields = {
            'id': ['iexact'],
        }


class ViolenceType(DjangoObjectType):
    class Meta:
        model = Violence
        exclude_fields = ('events',)

    sub_types = DjangoPaginatedListObjectField(
        ViolenceSubObjectListType,
        related_name='sub_types',
        reverse_related_name='violence',
    )


class ViolenceListType(CustomDjangoListObjectType):
    class Meta:
        model = Violence
        filter_fields = {
            'id': ['iexact'],
        }


class ActorType(DjangoObjectType):
    class Meta:
        model = Actor
        exclude_fields = ('events',)


class ActorListType(CustomDjangoListObjectType):
    class Meta:
        model = Actor
        filterset_class = ActorFilter


class DisasterSubObjectType(DjangoObjectType):
    class Meta:
        model = DisasterSubType
        exclude_fields = ('events', 'type')


class DisasterSubObjectListType(CustomDjangoListObjectType):
    class Meta:
        model = DisasterSubType
        filter_fields = {
            'name': ['unaccent__icontains'],
        }


class DisasterTypeObjectType(DjangoObjectType):
    class Meta:
        model = DisasterType
        exclude_fields = ('events', 'disaster_sub_category')

    sub_types = DjangoPaginatedListObjectField(
        DisasterSubObjectListType,
        related_name='sub_types',
        reverse_related_name='type',
    )


class DisasterTypeObjectListType(CustomDjangoListObjectType):
    class Meta:
        model = DisasterType
        filter_fields = {
            'name': ['unaccent__icontains'],
        }


class DisasterSubCategoryType(DjangoObjectType):
    class Meta:
        model = DisasterSubCategory
        exclude_fields = ('events', 'category')

    types = DjangoPaginatedListObjectField(
        DisasterTypeObjectListType,
        related_name='types',
        reverse_related_name='disaster_sub_category',
    )


class DisasterSubCategoryListType(CustomDjangoListObjectType):
    class Meta:
        model = DisasterSubCategory
        filter_fields = {
            'name': ['unaccent__icontains'],
        }


class DisasterCategoryType(DjangoObjectType):
    class Meta:
        model = DisasterCategory
        exclude_fields = ('events',)

    sub_categories = DjangoPaginatedListObjectField(
        DisasterSubCategoryListType,
        related_name='sub_categories',
        reverse_related_name='category',
    )


class DisasterCategoryListType(CustomDjangoListObjectType):
    class Meta:
        model = DisasterCategory
        filter_fields = {
            'name': ['unaccent__icontains'],
        }


class EventReviewCountType(graphene.ObjectType):
    under_review_count = graphene.Int(required=False)
    signed_off_count = graphene.Int(required=False)
    review_complete_count = graphene.Int(required=False)
    to_be_reviewed_count = graphene.Int(required=False)


class OsvSubObjectType(DjangoObjectType):
    class Meta:
        model = OsvSubType
        filter_fields = {
            'name': ['icontains']
        }


class OsvSubTypeList(CustomDjangoListObjectType):
    class Meta:
        model = OsvSubType
        filter_fields = {
            'name': ['icontains']
        }


class EventType(DjangoObjectType):
    class Meta:
        model = Event
        exclude_fields = ('entries',)

    event_type = graphene.Field(CrisisTypeGrapheneEnum)
    other_sub_type = graphene.Field(EventOtherSubTypeEnum)
    trigger = graphene.Field(TriggerType)
    trigger_sub_type = graphene.Field(TriggerSubObjectType)
    violence = graphene.Field(ViolenceType)
    violence_sub_type = graphene.Field(ViolenceSubObjectType)
    actor = graphene.Field(ActorType)
    total_stock_idp_figures = graphene.Field(graphene.Int)
    total_flow_nd_figures = graphene.Field(graphene.Int)
    start_date_accuracy = graphene.Field(DateAccuracyGrapheneEnum)
    end_date_accuracy = graphene.Field(DateAccuracyGrapheneEnum)
    review_count = graphene.Field(EventReviewCountType)
    entry_count = graphene.Field(graphene.Int)
    glide_numbers = graphene.List(graphene.NonNull(graphene.String))
    osv_sub_type = graphene.Field(OsvSubObjectType)
    QA_RULE_TYPE = graphene.Field(QaRecommendedFigureEnum)

    def resolve_review_count(root, info, **kwargs):
        return info.context.event_event_review_count_dataloader.load(root.id)

    def resolve_entry_count(root, info, **kwargs):
        return info.context.event_entry_count_dataloader.load(root.id)

    def resolve_total_stock_idp_figures(root, info, **kwargs):
        NULL = 'null'
        value = getattr(
            root,
            Event.IDP_FIGURES_ANNOTATE,
            NULL
        )
        if value != NULL:
            return value
        return info.context.event_event_total_stock_idp_figures.load(root.id)

    def resolve_total_flow_nd_figures(root, info, **kwargs):
        NULL = 'null'
        value = getattr(
            root,
            Event.ND_FIGURES_ANNOTATE,
            NULL
        )
        if value != NULL:
            return value
        return info.context.event_event_total_flow_nd_figures.load(root.id)


class EventListType(CustomDjangoListObjectType):
    class Meta:
        model = Event
        filterset_class = EventFilter


class Query:
    trigger_list = DjangoPaginatedListObjectField(TriggerListType)
    sub_trigger_list = DjangoPaginatedListObjectField(TriggerSubObjectListType)
    violence_list = DjangoPaginatedListObjectField(ViolenceListType)
    actor = DjangoObjectField(ActorType)
    actor_list = DjangoPaginatedListObjectField(ActorListType,
                                                pagination=PageGraphqlPaginationWithoutCount(
                                                    page_size_query_param='pageSize'
                                                ))
    disaster_category_list = DjangoPaginatedListObjectField(DisasterCategoryListType)
    disaster_sub_category_list = DjangoPaginatedListObjectField(DisasterSubCategoryListType)
    disaster_type_list = DjangoPaginatedListObjectField(DisasterTypeObjectListType)
    disaster_sub_type_list = DjangoPaginatedListObjectField(DisasterSubObjectListType)

    event = DjangoObjectField(EventType)
    event_list = DjangoPaginatedListObjectField(EventListType,
                                                pagination=PageGraphqlPaginationWithoutCount(
                                                    page_size_query_param='pageSize'
                                                ))
    osv_sub_type_list = DjangoPaginatedListObjectField(OsvSubTypeList)
