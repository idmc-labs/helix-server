import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField
from utils.graphene.enums import EnumDescription
from apps.contrib.commons import DateAccuracyGrapheneEnum
from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.event.enums import (
    QaRecommendedFigureEnum,
    EventReviewStatusEnum,
    EventCodeTypeGrapheneEnum,
)
from apps.event.models import (
    Event,
    EventCode,
    Violence,
    ViolenceSubType,
    Actor,
    DisasterSubCategory,
    DisasterCategory,
    DisasterSubType,
    DisasterType,
    OsvSubType,
    ContextOfViolence,
    OtherSubType,
)
from apps.event.filters import (
    ActorFilter,
    EventFilter,
    DisasterSubTypeFilter,
    DisasterTypeFilter,
    DisasterCategoryFilter,
    DisasterSubCategoryFilter,
    OsvSubTypeFilter,
    OtherSubTypeFilter,
    ContextOfViolenceFilter,
    ViolenceFilter,
    ViolenceSubTypeFilter,
)
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.pagination import PageGraphqlPaginationWithoutCount


class ViolenceSubObjectType(DjangoObjectType):
    class Meta:
        model = ViolenceSubType
        exclude_fields = ('events', 'violence')


class ViolenceSubObjectListType(CustomDjangoListObjectType):
    class Meta:
        model = ViolenceSubType
        filterset_class = ViolenceSubTypeFilter


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
        filterset_class = ViolenceFilter


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
        filterset_class = DisasterSubTypeFilter


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
        filterset_class = DisasterTypeFilter


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
        filterset_class = DisasterSubCategoryFilter


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
        filterset_class = DisasterCategoryFilter


class EventReviewCountType(graphene.ObjectType):
    review_not_started_count = graphene.Int(required=False)
    review_in_progress_count = graphene.Int(required=False)
    review_re_request_count = graphene.Int(required=False)
    review_approved_count = graphene.Int(required=False)
    total_count = graphene.Int(required=False)
    progress = graphene.Float(required=False)


class OsvSubObjectType(DjangoObjectType):
    class Meta:
        model = OsvSubType
        filterset_class = OsvSubTypeFilter


class OsvSubTypeList(CustomDjangoListObjectType):
    class Meta:
        model = OsvSubType
        filterset_class = OsvSubTypeFilter


class OtherSubTypeObjectType(DjangoObjectType):
    class Meta:
        model = OtherSubType
        filterset_class = OtherSubTypeFilter


class OtherSubTypeList(CustomDjangoListObjectType):
    class Meta:
        model = OtherSubType
        filterset_class = OtherSubTypeFilter


class EventCodeType(DjangoObjectType):
    event_code_type = graphene.Field(EventCodeTypeGrapheneEnum)
    event_code_display = EnumDescription(source='get_event_code_type_display')

    class Meta:
        model = EventCode
        fields = ('id', 'uuid', 'event_code', 'event_code_type', 'country')


class EventType(DjangoObjectType):

    class Meta:
        model = Event
        exclude_fields = ('figures', 'gidd_events', 'glide_numbers')

    event_type = graphene.Field(CrisisTypeGrapheneEnum)
    event_type_display = EnumDescription(source='get_event_type_display')
    other_sub_type = graphene.Field(OtherSubTypeObjectType)
    violence = graphene.Field(ViolenceType)
    violence_sub_type = graphene.Field(ViolenceSubObjectType)
    actor = graphene.Field(ActorType)
    total_stock_idp_figures = graphene.Field(graphene.Int)
    stock_idp_figures_max_end_date = graphene.Field(graphene.Date, required=False)
    total_flow_nd_figures = graphene.Field(graphene.Int)
    start_date_accuracy = graphene.Field(DateAccuracyGrapheneEnum)
    start_date_accuracy_display = EnumDescription(source='get_start_date_accuracy_display')
    end_date_accuracy = graphene.Field(DateAccuracyGrapheneEnum)
    end_date_accuracy_display = EnumDescription(source='get_end_date_accuracy_display')
    entry_count = graphene.Field(graphene.Int)
    osv_sub_type = graphene.Field(OsvSubObjectType)
    qa_rule_type = graphene.Field(QaRecommendedFigureEnum)
    qs_rule_type_display = EnumDescription(source='get_qs_rule_type_display')
    event_typology = graphene.String()
    figure_typology = graphene.List(graphene.String)
    review_status = graphene.Field(EventReviewStatusEnum)
    review_status_display = EnumDescription(source='get_review_status_display')
    review_count = graphene.Field(EventReviewCountType)
    event_codes = graphene.List(graphene.NonNull(EventCodeType))
    crisis = graphene.Field('apps.crisis.schema.CrisisType')

    def resolve_crisis(root, info, **kwargs):
        return info.context.event_crisis_loader.load(root.id)

    def resolve_event_codes(root, info, **kwargs):
        return info.context.event_code_loader.load(root.id)

    def resolve_entry_count(root, info, **kwargs):
        return info.context.event_entry_count_dataloader.load(root.id)

    def resolve_event_typology(root, info, **kwargs):
        return info.context.event_typology_dataloader.load(root.id)

    def resolve_figure_typology(root, info, **kwargs):
        return info.context.event_figure_typology_dataloader.load(root.id)

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

    def resolve_stock_idp_figures_max_end_date(root, info, **kwargs):
        NULL = 'null'
        value = getattr(
            root,
            Event.IDP_FIGURES_REFERENCE_DATE_ANNOTATE,
            NULL
        )
        if value != NULL:
            return value
        return info.context.event_stock_idp_figures_max_end_date.load(root.id)

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

    def resolve_review_count(root, info, **kwargs):
        return info.context.event_review_count_dataloader.load(root.id)


class EventListType(CustomDjangoListObjectType):
    class Meta:
        model = Event
        filterset_class = EventFilter


class ContextOfViolenceType(DjangoObjectType):
    class Meta:
        model = ContextOfViolence
        filterset_class = ContextOfViolenceFilter


class ContextOfViolenceListType(CustomDjangoListObjectType):
    class Meta:
        model = ContextOfViolence
        filterset_class = ContextOfViolenceFilter


class Query:
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
    context_of_violence = DjangoObjectField(ContextOfViolenceType)
    context_of_violence_list = DjangoPaginatedListObjectField(ContextOfViolenceListType)
    other_sub_type_list = DjangoPaginatedListObjectField(OtherSubTypeList)
