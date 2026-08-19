import logging

import graphene
from django.db.models import Case, ExpressionWrapper, JSONField, Q, Sum, When, fields
from django.db.models.functions import ExtractYear
from graphene import ObjectType
from graphene.types.generic import GenericScalar
from graphene_django_extras import DjangoObjectField
from graphene_django_extras.converter import convert_django_field

from apps.contrib.commons import DateAccuracyGrapheneEnum
from apps.contrib.enums import PreviewStatusGrapheneEnum
from apps.contrib.models import SourcePreview
from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.crisis.models import Crisis
from apps.entry.enums import (
    AccuracyGrapheneEnum,
    DisplacementOccurredGrapheneEnum,
    FigureCategoryTypeEnum,
    FigureReviewStatusEnum,
    FigureSourcesReliabilityEnum,
    FigureTermsEnum,
    GenderTypeGrapheneEnum,
    GeocoderGrapheneEnum,
    IdentifierGrapheneEnum,
    PcodeAccuracyGrapheneEnum,
    QuantifierGrapheneEnum,
    RoleGrapheneEnum,
    UnitGrapheneEnum,
)
from apps.entry.filters import (
    DisaggregatedAgeFilter,
    FigureFilter,
    FigureLocationFilter,
    FigureTagFilter,
)
from apps.entry.models import (
    DisaggregatedAge,
    Entry,
    Figure,
    FigureLocation,
    FigureTag,
)
from apps.event.schema import EventType, OtherSubTypeObjectType
from apps.extraction.filters import (
    EntryExtractionFilterSet,
    FigureExtractionFilterDataInputType,
    FigureExtractionFilterSet,
    ReportFigureExtractionFilterSet,
)
from apps.organization.schema import OrganizationListType
from apps.review.enums import ReviewCommentTypeEnum, ReviewFieldTypeEnum
from utils.graphene.enums import EnumDescription
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.pagination import PageGraphqlPaginationWithoutCount
from utils.graphene.relation_loaders import RelationBatchedDjangoObjectType
from utils.graphene.types import CustomDjangoListObjectType

logger = logging.getLogger(__name__)


@convert_django_field.register(JSONField)
def convert_json_field_to_scalar(field, registry=None):
    # https://github.com/graphql-python/graphene-django/issues/303#issuecomment-339939955
    return GenericScalar()


class DisaggregatedAgeType(RelationBatchedDjangoObjectType):
    class Meta:
        model = DisaggregatedAge
        # entry_figure_related and report_report_related are unbounded fan-out. figureList has no
        # disaggregated-age filter, and reportList cannot filter on a report's stored age
        # disaggregation, so neither has a bounded replacement.
        exclude_fields = ("entry_figure_related", "report_report_related")

    uuid = graphene.String(required=True)
    age_from = graphene.Field(graphene.Int)
    age_to = graphene.Field(graphene.Int)
    sex = graphene.Field(GenderTypeGrapheneEnum)
    sex_display = EnumDescription(source="get_sex_display")


class DisaggregatedAgeListType(CustomDjangoListObjectType):
    class Meta:
        model = DisaggregatedAge
        filterset_class = DisaggregatedAgeFilter


class DisaggregatedStratumType(ObjectType):
    uuid = graphene.String(required=True)
    date = graphene.String()  # because inside the json field
    value = graphene.Int()


class FigureLocationType(RelationBatchedDjangoObjectType):
    class Meta:
        model = FigureLocation
        # figures is unbounded fan-out; figureList has no geo-location filter, so there is
        # no bounded replacement for it.
        exclude_fields = ("figures",)

    accuracy = graphene.Field(AccuracyGrapheneEnum)
    accuracy_display = EnumDescription(source="get_accuracy_display")
    identifier = graphene.Field(IdentifierGrapheneEnum)
    identifier_display = EnumDescription(source="get_identifier_display")
    geocoder = graphene.Field(GeocoderGrapheneEnum)
    geocoder_display = EnumDescription(source="get_geocoder_display")
    pcode_accuracy = graphene.Field(PcodeAccuracyGrapheneEnum)
    pcode_accuracy_display = EnumDescription(source="get_pcode_accuracy_display")


class FigureLocationListType(CustomDjangoListObjectType):
    class Meta:
        model = FigureLocation
        filterset_class = FigureLocationFilter


class FigureTagType(RelationBatchedDjangoObjectType):
    class Meta:
        model = FigureTag
        # figure_set is unbounded fan-out; figures are read via
        # figureList(filters: {filterFigureTags: [id]}), a strict membership test that reproduces
        # the removed set exactly (895 figures on the widest tag).
        exclude_fields = ("figure_set",)


class FigureLastReviewCommentStatusType(ObjectType):
    id = graphene.ID(required=True)
    field = graphene.Field(ReviewFieldTypeEnum, required=True)
    comment_type = graphene.Field(ReviewCommentTypeEnum, required=True)


class FigureType(RelationBatchedDjangoObjectType):
    class Meta:
        # report_set is unbounded fan-out: the reports that pinned this figure into their figure
        # set. reportList cannot filter by a member figure, so it has no bounded replacement.
        exclude_fields = ("figure_reviews", "report_set")
        model = Figure

    quantifier = graphene.Field(QuantifierGrapheneEnum)
    get_quantifier = EnumDescription(source="get_quantifier_display")
    unit = graphene.Field(UnitGrapheneEnum)
    unit_display = EnumDescription(source="get_unit_display")
    role = graphene.Field(RoleGrapheneEnum)
    role_display = EnumDescription(source="get_role_display")
    displacement_occurred = graphene.Field(DisplacementOccurredGrapheneEnum)
    displacement_occurred_display = EnumDescription(source="get_displacement_occurred_display")
    disaggregation_age = DjangoPaginatedListObjectField(DisaggregatedAgeListType, related_name="disaggregation_age")
    disaggregation_strata_json = graphene.List(graphene.NonNull(DisaggregatedStratumType))
    geo_locations = DjangoPaginatedListObjectField(
        FigureLocationListType,
        related_name="geo_locations",
    )
    start_date_accuracy = graphene.Field(DateAccuracyGrapheneEnum)
    start_date_accuracy_display = EnumDescription(source="get_start_date_accuracy_display")
    end_date_accuracy = graphene.Field(DateAccuracyGrapheneEnum)
    end_date_accuracy_display = EnumDescription(source="get_end_date_accuracy_display")
    category = graphene.Field(FigureCategoryTypeEnum)
    category_display = EnumDescription(source="get_category_display")
    term = graphene.Field(FigureTermsEnum)
    term_display = EnumDescription(source="get_term_display")
    figure_cause = graphene.Field(CrisisTypeGrapheneEnum)
    figure_cause_display = EnumDescription(source="get_figure_cause_display")
    other_sub_type = graphene.Field(OtherSubTypeObjectType)
    figure_typology = graphene.String()
    sources = DjangoPaginatedListObjectField(
        OrganizationListType,
        related_name="sources",
        reverse_related_name="sourced_figures",
    )
    stock_date = graphene.Date()
    stock_reporting_date = graphene.Date()
    flow_start_date = graphene.Date()
    flow_end_date = graphene.Date()
    geolocations = graphene.String()
    sources_reliability = graphene.Field(FigureSourcesReliabilityEnum)
    review_status = graphene.Field(FigureReviewStatusEnum)
    review_status_display = EnumDescription(source="get_review_status_display")
    last_review_comment_status = graphene.List(graphene.NonNull(FigureLastReviewCommentStatusType))
    event = graphene.Field(EventType, required=True)
    event_id = graphene.ID(required=True, source="event_id")
    entry = graphene.Field("apps.entry.schema.EntryType", required=True)
    entry_id = graphene.ID(required=True, source="entry_id")
    # UUID of the hulk relation row, or null if the entity was not created
    # through the pyhelix (hulk/bulk) interface. Presence flags a hulk import;
    # the value tallies against the bulk-import input dataset.
    hulk_uuid = graphene.UUID()

    def resolve_hulk_uuid(root, info, **kwargs):
        return info.context.figure_hulk_dataloader.load(root.id).then(lambda row: row.uuid if row else None)

    def resolve_stock_date(root, info, **kwargs):
        if root.category in Figure.stock_list():
            return root.start_date

    def resolve_stock_reporting_date(root, info, **kwargs):
        if root.category in Figure.stock_list():
            return root.end_date

    def resolve_flow_start_date(root, info, **kwargs):
        if root.category in Figure.flow_list():
            return root.start_date

    def resolve_flow_end_date(root, info, **kwargs):
        if root.category in Figure.flow_list():
            return root.end_date

    def resolve_figure_typology(root, info, **kwargs):
        return info.context.figure_typology_dataloader.load(root.id)

    def resolve_geolocations(root, info, **kwargs):
        return info.context.figure_geolocations_loader.load(root.id)

    def resolve_sources_reliability(root, info, **kwargs):
        return info.context.figure_sources_reliability_loader.load(root.id)

    def resolve_last_review_comment_status(root, info, **kwargs):
        return info.context.last_review_comment_status_loader.load(root.id)

    # entry (forward FK) is auto-wired via RelationBatchedDjangoObjectType -> RelationNodeLoader.


class FigureListType(CustomDjangoListObjectType):
    class Meta:
        model = Figure
        filterset_class = FigureFilter


class TotalFigureFilterInputType(graphene.InputObjectType):
    categories = graphene.List(graphene.NonNull(graphene.String))
    filter_figure_start_after = graphene.Date()
    filter_figure_end_before = graphene.Date()
    roles = graphene.List(graphene.NonNull(graphene.String))


class EntryType(RelationBatchedDjangoObjectType):
    class Meta:
        model = Entry
        exclude_fields = (
            "reviewers",
            "review_status",
            "review_comments",
            "reviewing",
            # Unbounded fan-out (an entry can own hundreds of figures) and no client
            # uses it: figures are read via figureList(filterFigureEntry). Without the
            # exclude, graphene-django auto-exposes the reverse relation as a plain list.
            "figures",
        )

    created_by = graphene.Field("apps.users.schema.UserType")
    last_modified_by = graphene.Field("apps.users.schema.UserType")
    publishers = DjangoPaginatedListObjectField(
        OrganizationListType,
        related_name="publishers",
        reverse_related_name="published_entries",
    )
    preview = graphene.Field("apps.entry.schema.SourcePreviewType")
    # See FigureType.hulk_uuid.
    hulk_uuid = graphene.UUID()

    def resolve_hulk_uuid(root, info, **kwargs):
        return info.context.entry_hulk_dataloader.load(root.id).then(lambda row: row.uuid if row else None)

    # document + preview (forward FKs) are auto-wired via RelationBatchedDjangoObjectType ->
    # RelationNodeLoader (no explicit resolver needed).


class EntryListType(CustomDjangoListObjectType):
    class Meta:
        model = Entry
        filterset_class = EntryExtractionFilterSet


class SourcePreviewType(RelationBatchedDjangoObjectType):
    class Meta:
        model = SourcePreview
        exclude_fields = ("entry", "token")

    status = graphene.Field(PreviewStatusGrapheneEnum)
    status_display = EnumDescription(source="get_status_display")
    # See FigureType.hulk_uuid.
    hulk_uuid = graphene.UUID()

    def resolve_hulk_uuid(root, info, **kwargs):
        return info.context.source_preview_hulk_dataloader.load(root.id).then(lambda row: row.uuid if row else None)

    def resolve_pdf(root, info, **kwargs):
        if root.status == SourcePreview.PREVIEW_STATUS.COMPLETED:
            return info.context.request.build_absolute_uri(root.pdf.url)
        return None


class VisualizationValueType(ObjectType):
    date = graphene.Date(required=True)
    value = graphene.Int(required=True)


class VisualizationFigureType(ObjectType):
    idps_conflict_figures = graphene.List(graphene.NonNull(VisualizationValueType))
    idps_disaster_figures = graphene.List(graphene.NonNull(VisualizationValueType))
    nds_conflict_figures = graphene.List(graphene.NonNull(VisualizationValueType))
    nds_disaster_figures = graphene.List(graphene.NonNull(VisualizationValueType))


class FigureTagListType(CustomDjangoListObjectType):
    class Meta:
        model = FigureTag
        filterset_class = FigureTagFilter


class Query:
    figure_tag = DjangoObjectField(FigureTagType)
    figure_tag_list = DjangoPaginatedListObjectField(
        FigureTagListType, pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize")
    )

    figure = DjangoObjectField(FigureType)
    figure_list = DjangoPaginatedListObjectField(
        FigureListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param="pageSize",
        ),
        filterset_class=FigureExtractionFilterSet,
    )
    source_preview = DjangoObjectField(SourcePreviewType)
    entry = DjangoObjectField(EntryType)
    entry_list = DjangoPaginatedListObjectField(
        EntryListType, pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize")
    )
    disaggregated_age = DjangoObjectField(DisaggregatedAgeType)
    figure_aggregations = graphene.Field(
        VisualizationFigureType,
        filters=FigureExtractionFilterDataInputType(required=True),
    )

    @staticmethod
    def resolve_figure_aggregations(_, info, filters):
        def _filter_nd_same_or_multiple_year_figures(qs, figure_cause):
            qs = qs.annotate(
                # NOTE: Once we upgrade django, let's rewrite this without two different annotations
                year_difference=ExpressionWrapper(
                    ExtractYear("end_date") - ExtractYear("start_date"), output_field=fields.IntegerField()
                ),
                canonical_date=Case(
                    When(
                        Q(year_difference__gt=0),
                        then="end_date",
                    ),
                    default="start_date",
                ),
            )

            return (
                qs.filter(
                    category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                    role=Figure.ROLE.RECOMMENDED,
                    figure_cause=figure_cause,
                )
                .values("canonical_date")
                .annotate(value=Sum("total_figures"))
            )

        figure_qs = ReportFigureExtractionFilterSet(data=filters).qs

        idps_conflict_figure_qs = (
            figure_qs.filter(
                category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
                role=Figure.ROLE.RECOMMENDED,
                figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            )
            .values("end_date")
            .annotate(value=Sum("total_figures"))
        )

        idps_disaster_figure_qs = (
            figure_qs.filter(
                category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
                role=Figure.ROLE.RECOMMENDED,
                figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            )
            .values("end_date")
            .annotate(value=Sum("total_figures"))
        )

        nds_conflict_figure_qs = _filter_nd_same_or_multiple_year_figures(
            figure_qs, figure_cause=Crisis.CRISIS_TYPE.CONFLICT
        )

        nds_disaster_figure_qs = _filter_nd_same_or_multiple_year_figures(
            figure_qs, figure_cause=Crisis.CRISIS_TYPE.DISASTER
        )

        return VisualizationFigureType(
            idps_conflict_figures=[
                VisualizationValueType(date=k["end_date"], value=k["value"]) for k in idps_conflict_figure_qs
            ],
            idps_disaster_figures=[
                VisualizationValueType(date=k["end_date"], value=k["value"]) for k in idps_disaster_figure_qs
            ],
            nds_conflict_figures=[
                VisualizationValueType(date=k["canonical_date"], value=k["value"]) for k in nds_conflict_figure_qs
            ],
            nds_disaster_figures=[
                VisualizationValueType(date=k["canonical_date"], value=k["value"]) for k in nds_disaster_figure_qs
            ],
        )
