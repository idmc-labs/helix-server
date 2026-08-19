import graphene
from graphene_django_extras import DjangoObjectField

from apps.contrib.commons import DateAccuracyGrapheneEnum
from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.event.enums import (
    EventCodeTypeGrapheneEnum,
    EventReviewStatusEnum,
    QaRecommendedFigureEnum,
)
from apps.event.filters import (
    ActorFilter,
    ContextOfViolenceFilter,
    DisasterCategoryFilter,
    DisasterSubCategoryFilter,
    DisasterSubTypeFilter,
    DisasterTypeFilter,
    EventFilter,
    OsvSubTypeFilter,
    OtherSubTypeFilter,
    ViolenceFilter,
    ViolenceSubTypeFilter,
)
from apps.event.models import (
    Actor,
    ContextOfViolence,
    DisasterCategory,
    DisasterSubCategory,
    DisasterSubType,
    DisasterType,
    Event,
    EventCode,
    OsvSubType,
    OtherSubType,
    Violence,
    ViolenceSubType,
)
from utils.graphene.enums import EnumDescription
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.pagination import PageGraphqlPaginationWithoutCount
from utils.graphene.relation_loaders import RelationBatchedDjangoObjectType, reverse_fk_list_resolver
from utils.graphene.types import CustomDjangoListObjectType


class ViolenceSubObjectType(RelationBatchedDjangoObjectType):
    class Meta:
        model = ViolenceSubType
        # figures, reportSet and extractionquerySet are unbounded fan-out. figures are read via
        # figureList(filters: {filterFigureViolenceSubTypes: [id], filterFigureCrisisTypes: ["CONFLICT"]}):
        # filterFigureViolenceSubTypes is pass-through, so on its own it also returns every figure
        # of another cause (28,307 -> 153,803 on the production dump); the crisis-type pairing
        # reproduces the removed set exactly, for every sub-type.
        # reportSet/extractionquerySet are the saved figure-filter selections of reports and
        # extraction queries; reportList and extractionQueryList cannot filter on them, so those
        # two have no bounded replacement.
        exclude_fields = ("events", "violence", "figures", "report_set", "extractionquery_set")


class ViolenceSubObjectListType(CustomDjangoListObjectType):
    class Meta:
        model = ViolenceSubType
        filterset_class = ViolenceSubTypeFilter


class ViolenceType(RelationBatchedDjangoObjectType):
    class Meta:
        model = Violence
        # figures, reportSet and extractionquerySet are unbounded fan-out. figures are read via
        # figureList(filters: {filterFigureViolenceTypes: [id], filterFigureCrisisTypes: ["CONFLICT"]}):
        # filterFigureViolenceTypes is pass-through, so on its own it also returns every figure of
        # another cause (28,307 -> 153,803 on the production dump); the crisis-type pairing
        # reproduces the removed set exactly, for every violence type.
        # reportSet/extractionquerySet are the saved figure-filter selections of reports and
        # extraction queries; reportList and extractionQueryList cannot filter on them, so those
        # two have no bounded replacement.
        exclude_fields = ("events", "figures", "report_set", "extractionquery_set")

    sub_types = DjangoPaginatedListObjectField(
        ViolenceSubObjectListType,
        related_name="sub_types",
        reverse_related_name="violence",
    )


class ViolenceListType(CustomDjangoListObjectType):
    class Meta:
        model = Violence
        filterset_class = ViolenceFilter


class ActorType(RelationBatchedDjangoObjectType):
    class Meta:
        model = Actor
        exclude_fields = ("events",)


class ActorListType(CustomDjangoListObjectType):
    class Meta:
        model = Actor
        filterset_class = ActorFilter


class DisasterSubObjectType(RelationBatchedDjangoObjectType):
    class Meta:
        model = DisasterSubType
        # figures, reportSet and extractionquerySet are unbounded fan-out. figures are read via
        # figureList(filters: {filterFigureDisasterSubTypes: [id], filterFigureCrisisTypes: ["DISASTER"]}):
        # filterFigureDisasterSubTypes is pass-through, so on its own it also returns every figure of
        # another cause (64,088 -> 125,296 on the production dump); the crisis-type pairing
        # reproduces the removed set exactly, for every sub-type.
        # reportSet/extractionquerySet are the saved figure-filter selections of reports and
        # extraction queries; reportList and extractionQueryList cannot filter on them, so those
        # two have no bounded replacement.
        exclude_fields = ("events", "type", "figures", "report_set", "extractionquery_set")


class DisasterSubObjectListType(CustomDjangoListObjectType):
    class Meta:
        model = DisasterSubType
        filterset_class = DisasterSubTypeFilter


class DisasterTypeObjectType(RelationBatchedDjangoObjectType):
    class Meta:
        model = DisasterType
        # figures, reportSet and extractionquerySet are unbounded fan-out. figures are read via
        # figureList(filters: {filterFigureDisasterTypes: [id], filterFigureCrisisTypes: ["DISASTER"]}):
        # filterFigureDisasterTypes is pass-through, so on its own it also returns every figure of
        # another cause (64,317 -> 125,525 on the production dump); the crisis-type pairing
        # reproduces the removed set exactly, for every type.
        # reportSet/extractionquerySet are the saved figure-filter selections of reports and
        # extraction queries; reportList and extractionQueryList cannot filter on them, so those
        # two have no bounded replacement.
        exclude_fields = ("events", "disaster_sub_category", "figures", "report_set", "extractionquery_set")

    sub_types = DjangoPaginatedListObjectField(
        DisasterSubObjectListType,
        related_name="sub_types",
        reverse_related_name="type",
    )


class DisasterTypeObjectListType(CustomDjangoListObjectType):
    class Meta:
        model = DisasterType
        filterset_class = DisasterTypeFilter


class DisasterSubCategoryType(RelationBatchedDjangoObjectType):
    class Meta:
        model = DisasterSubCategory
        # figures, reportSet and extractionquerySet are unbounded fan-out. figures are read via
        # figureList(filters: {filterFigureDisasterSubCategories: [id], filterFigureCrisisTypes: ["DISASTER"]}):
        # filterFigureDisasterSubCategories is pass-through, so on its own it also returns every figure
        # of another cause (71,823 -> 133,031 on the production dump); the crisis-type pairing
        # reproduces the removed set exactly, for every sub-category.
        # reportSet/extractionquerySet are the saved figure-filter selections of reports and
        # extraction queries; reportList and extractionQueryList cannot filter on them, so those
        # two have no bounded replacement.
        exclude_fields = ("events", "category", "figures", "report_set", "extractionquery_set")

    types = DjangoPaginatedListObjectField(
        DisasterTypeObjectListType,
        related_name="types",
        reverse_related_name="disaster_sub_category",
    )


class DisasterSubCategoryListType(CustomDjangoListObjectType):
    class Meta:
        model = DisasterSubCategory
        filterset_class = DisasterSubCategoryFilter


class DisasterCategoryType(RelationBatchedDjangoObjectType):
    class Meta:
        model = DisasterCategory
        # figures, reportSet and extractionquerySet are unbounded fan-out. figures are read via
        # figureList(filters: {filterFigureDisasterCategories: [id], filterFigureCrisisTypes: ["DISASTER"]}):
        # filterFigureDisasterCategories is pass-through, so on its own it also returns every figure of
        # another cause (116,414 -> 177,622 on the production dump); the crisis-type pairing
        # reproduces the removed set exactly, for every category.
        # reportSet/extractionquerySet are the saved figure-filter selections of reports and
        # extraction queries; reportList and extractionQueryList cannot filter on them, so those
        # two have no bounded replacement.
        exclude_fields = ("events", "figures", "report_set", "extractionquery_set")

    sub_categories = DjangoPaginatedListObjectField(
        DisasterSubCategoryListType,
        related_name="sub_categories",
        reverse_related_name="category",
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


class OsvSubObjectType(RelationBatchedDjangoObjectType):
    class Meta:
        model = OsvSubType
        filterset_class = OsvSubTypeFilter
        # figures, events, reportSet and extractionquerySet are unbounded fan-out, and none of the
        # four has an exact bounded replacement.
        # filterFigureOsvSubTypes keys off event.violence.name rather than a figure column, so it
        # passes through every figure whose event is not OSV and no combination of the figure
        # filters recovers the set: measured on one sub-type, the removed field returned 372
        # figures while the closest pairing (filterFigureOsvSubTypes + filterFigureCrisisTypes:
        # ["CONFLICT"] + filterFigureViolenceTypes: [<OSV>]) returned 2,524 -- 2,316 extra and 164
        # short, because 172 of the 571 figures carrying an osv_sub_type do not carry the OSV
        # violence themselves.
        # For events the closest is eventList(filters: {eventTypes: ["CONFLICT"],
        # violenceTypes: [<OSV>], osvSubTypeByIds: [id]}); it is short by the 7 events whose
        # osv_sub_type is set while their violence is not OSV (50 -> 46 on the largest sub-type,
        # 3 of the 6 populated sub-types affected) -- data worth correcting separately.
        # reportSet/extractionquerySet are the saved figure-filter selections of reports and
        # extraction queries; reportList and extractionQueryList cannot filter on them.
        exclude_fields = ("figures", "events", "report_set", "extractionquery_set")


class OsvSubTypeList(CustomDjangoListObjectType):
    class Meta:
        model = OsvSubType
        filterset_class = OsvSubTypeFilter


class OtherSubTypeObjectType(RelationBatchedDjangoObjectType):
    class Meta:
        model = OtherSubType
        filterset_class = OtherSubTypeFilter
        # figures and events are unbounded fan-out; events are read via
        # eventList(filters: {eventTypes: ["OTHER"], otherSubTypes: [id]}) -- otherSubTypes is
        # pass-through, so the eventTypes pairing is what reproduces the removed set exactly.
        # figureList has no other-sub-type filter, so figures have no bounded replacement.
        exclude_fields = ("figures", "events")


class OtherSubTypeList(CustomDjangoListObjectType):
    class Meta:
        model = OtherSubType
        filterset_class = OtherSubTypeFilter


class EventCodeType(RelationBatchedDjangoObjectType):
    event_code_type = graphene.Field(EventCodeTypeGrapheneEnum)
    event_code_display = EnumDescription(source="get_event_code_type_display")

    class Meta:
        model = EventCode
        fields = ("id", "uuid", "event_code", "event_code_type", "country")


class EventType(RelationBatchedDjangoObjectType):
    class Meta:
        model = Event
        # reportSet/extractionquerySet are the reports and saved extraction queries whose stored
        # figure filter names this event; reportList and extractionQueryList cannot filter on that
        # selection, so neither has a bounded replacement.
        exclude_fields = ("figures", "gidd_events", "glide_numbers", "report_set", "extractionquery_set")

    event_type = graphene.Field(CrisisTypeGrapheneEnum)
    event_type_display = EnumDescription(source="get_event_type_display")
    other_sub_type = graphene.Field(OtherSubTypeObjectType)
    violence = graphene.Field(ViolenceType)
    violence_sub_type = graphene.Field(ViolenceSubObjectType)
    actor = graphene.Field(ActorType)
    total_stock_idp_figures = graphene.Field(graphene.Int)
    stock_idp_figures_max_end_date = graphene.Field(graphene.Date, required=False)
    total_flow_nd_figures = graphene.Field(graphene.Int)
    start_date_accuracy = graphene.Field(DateAccuracyGrapheneEnum)
    start_date_accuracy_display = EnumDescription(source="get_start_date_accuracy_display")
    end_date_accuracy = graphene.Field(DateAccuracyGrapheneEnum)
    end_date_accuracy_display = EnumDescription(source="get_end_date_accuracy_display")
    entry_count = graphene.Field(graphene.Int)
    osv_sub_type = graphene.Field(OsvSubObjectType)
    qa_rule_type = graphene.Field(QaRecommendedFigureEnum)
    qs_rule_type_display = EnumDescription(source="get_qs_rule_type_display")
    event_typology = graphene.String()
    figure_typology = graphene.List(graphene.String)
    review_status = graphene.Field(EventReviewStatusEnum)
    review_status_display = EnumDescription(source="get_review_status_display")
    review_count = graphene.Field(EventReviewCountType)
    event_codes = graphene.List(graphene.NonNull(EventCodeType))
    crisis = graphene.Field("apps.crisis.schema.CrisisType")
    crisis_id = graphene.ID(required=True, source="crisis_id")
    # See FigureType.hulk_uuid.
    hulk_uuid = graphene.UUID()

    # crisis (forward FK) is auto-wired via RelationBatchedDjangoObjectType -> RelationNodeLoader.

    def resolve_hulk_uuid(root, info, **kwargs):
        return info.context.event_hulk_dataloader.load(root.id).then(lambda row: row.uuid if row else None)

    # The GraphQL field name (event_codes) != the model reverse accessor (event.event_code),
    # so the auto-wire can't map it; wire it explicitly through the same factory the auto-wire
    # uses, so the ref (and the per-request loader) is shared with the `event_code` field.
    # An event with no codes resolves to an empty list (consistent with the other list loaders).
    resolve_event_codes = reverse_fk_list_resolver(EventCode, "event")

    def resolve_entry_count(root, info, **kwargs):
        return info.context.event_entry_count_dataloader.load(root.id)

    def resolve_event_typology(root, info, **kwargs):
        return info.context.event_typology_dataloader.load(root.id)

    def resolve_figure_typology(root, info, **kwargs):
        return info.context.event_figure_typology_dataloader.load(root.id)

    def resolve_total_stock_idp_figures(root, info, **kwargs):
        NULL = "null"
        value = getattr(root, Event.IDP_FIGURES_ANNOTATE, NULL)
        if value != NULL:
            return value
        return info.context.event_event_total_stock_idp_figures.load(root.id)

    def resolve_stock_idp_figures_max_end_date(root, info, **kwargs):
        NULL = "null"
        value = getattr(root, Event.IDP_FIGURES_REFERENCE_DATE_ANNOTATE, NULL)
        if value != NULL:
            return value
        return info.context.event_stock_idp_figures_max_end_date.load(root.id)

    def resolve_total_flow_nd_figures(root, info, **kwargs):
        NULL = "null"
        value = getattr(root, Event.ND_FIGURES_ANNOTATE, NULL)
        if value != NULL:
            return value
        return info.context.event_event_total_flow_nd_figures.load(root.id)

    def resolve_review_count(root, info, **kwargs):
        return info.context.event_review_count_dataloader.load(root.id)


class EventListType(CustomDjangoListObjectType):
    class Meta:
        model = Event
        filterset_class = EventFilter


class ContextOfViolenceType(RelationBatchedDjangoObjectType):
    class Meta:
        model = ContextOfViolence
        filterset_class = ContextOfViolenceFilter
        # figures, events, reportSet and extractionquerySet are unbounded fan-out. Both
        # figureList(filters: {filterFigureContextOfViolence: [id]}) and
        # eventList(filters: {contextOfViolences: [id]}) are strict membership tests and reproduce
        # the removed sets exactly (619 figures / 252 events on the widest context).
        # reportSet/extractionquerySet are the saved figure-filter selections of reports and
        # extraction queries; reportList and extractionQueryList cannot filter on them, so those
        # two have no bounded replacement.
        exclude_fields = ("figures", "events", "report_set", "extractionquery_set")


class ContextOfViolenceListType(CustomDjangoListObjectType):
    class Meta:
        model = ContextOfViolence
        filterset_class = ContextOfViolenceFilter


class Query:
    violence_list = DjangoPaginatedListObjectField(ViolenceListType)
    actor = DjangoObjectField(ActorType)
    actor_list = DjangoPaginatedListObjectField(
        ActorListType, pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize")
    )
    disaster_category_list = DjangoPaginatedListObjectField(DisasterCategoryListType)
    disaster_sub_category_list = DjangoPaginatedListObjectField(DisasterSubCategoryListType)
    disaster_type_list = DjangoPaginatedListObjectField(DisasterTypeObjectListType)
    disaster_sub_type_list = DjangoPaginatedListObjectField(DisasterSubObjectListType)

    event = DjangoObjectField(EventType)
    event_list = DjangoPaginatedListObjectField(
        EventListType, pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize")
    )
    osv_sub_type_list = DjangoPaginatedListObjectField(OsvSubTypeList)
    context_of_violence = DjangoObjectField(ContextOfViolenceType)
    context_of_violence_list = DjangoPaginatedListObjectField(ContextOfViolenceListType)
    other_sub_type_list = DjangoPaginatedListObjectField(OtherSubTypeList)
