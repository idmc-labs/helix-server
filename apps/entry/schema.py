import graphene
from django.db.models import JSONField, Sum
from graphene import ObjectType
from graphene.types.generic import GenericScalar
from graphene_django import DjangoObjectType
from graphene_django_extras.converter import convert_django_field
from graphene_django_extras import DjangoObjectField
import logging
from utils.graphene.enums import EnumDescription

from apps.entry.enums import (
    GenderTypeGrapheneEnum,
    QuantifierGrapheneEnum,
    UnitGrapheneEnum,
    RoleGrapheneEnum,
    DisplacementOccurredGrapheneEnum,
    OSMAccuracyGrapheneEnum,
    IdentifierGrapheneEnum,
    FigureCategoryTypeEnum,
    FigureTermsEnum,
    FigureSourcesReliabilityEnum,
    FigureReviewStatusEnum,
)
from apps.entry.filters import (
    OSMNameFilter,
    DisaggregatedAgeFilter,
    FigureFilter,
    FigureTagFilter,
)
from apps.entry.models import (
    Figure,
    FigureTag,
    Entry,
    OSMName,
    DisaggregatedAge,
)
from apps.contrib.models import SourcePreview
from apps.contrib.enums import PreviewStatusGrapheneEnum
from apps.contrib.commons import DateAccuracyGrapheneEnum
from apps.organization.schema import OrganizationListType
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.pagination import PageGraphqlPaginationWithoutCount
from apps.extraction.filters import (
    FigureExtractionFilterSet,
    FigureExtractionFilterDataInputType,
    EntryExtractionFilterSet,
)
from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.crisis.models import Crisis
from apps.event.schema import OtherSubTypeObjectType
from apps.review.enums import ReviewCommentTypeEnum, ReviewFieldTypeEnum

logger = logging.getLogger(__name__)


@convert_django_field.register(JSONField)
def convert_json_field_to_scalar(field, registry=None):
    # https://github.com/graphql-python/graphene-django/issues/303#issuecomment-339939955
    return GenericScalar()


class DisaggregatedAgeType(DjangoObjectType):
    class Meta:
        model = DisaggregatedAge
    uuid = graphene.String(required=True)
    age_from = graphene.Field(graphene.Int)
    age_to = graphene.Field(graphene.Int)
    sex = graphene.Field(GenderTypeGrapheneEnum)
    sex_display = EnumDescription(source='get_sex_display')


class DisaggregatedAgeListType(CustomDjangoListObjectType):
    class Meta:
        model = DisaggregatedAge
        filterset_class = DisaggregatedAgeFilter


class DisaggregatedStratumType(ObjectType):
    uuid = graphene.String(required=True)
    date = graphene.String()  # because inside the json field
    value = graphene.Int()


class OSMNameType(DjangoObjectType):
    class Meta:
        model = OSMName

    accuracy = graphene.Field(OSMAccuracyGrapheneEnum)
    accuracy_display = EnumDescription(source='get_accuracy_display')
    identifier = graphene.Field(IdentifierGrapheneEnum)
    identifier_display = EnumDescription(source='get_identifier_display')


class OSMNameListType(CustomDjangoListObjectType):
    class Meta:
        model = OSMName
        filterset_class = OSMNameFilter


class FigureTagType(DjangoObjectType):
    class Meta:
        model = FigureTag
        exclude_fields = ('entry_set',)


class FigureLastReviewCommentStatusType(ObjectType):
    id = graphene.ID(required=True)
    field = graphene.Field(ReviewFieldTypeEnum, required=True)
    comment_type = graphene.Field(ReviewCommentTypeEnum, required=True)


class FigureType(DjangoObjectType):
    class Meta:
        exclude_fields = (
            'figure_reviews',
        )
        model = Figure

    quantifier = graphene.Field(QuantifierGrapheneEnum)
    get_quantifier = EnumDescription(source='get_quantifier_display')
    unit = graphene.Field(UnitGrapheneEnum)
    unit_display = EnumDescription(source='get_unit_display')
    role = graphene.Field(RoleGrapheneEnum)
    role_display = EnumDescription(source='get_role_display')
    displacement_occurred = graphene.Field(DisplacementOccurredGrapheneEnum)
    displacement_occurred_display = EnumDescription(source='get_displacement_occurred_display')
    disaggregation_age = DjangoPaginatedListObjectField(
        DisaggregatedAgeListType,
        related_name="disaggregation_age"
    )
    disaggregation_strata_json = graphene.List(graphene.NonNull(DisaggregatedStratumType))
    geo_locations = DjangoPaginatedListObjectField(
        OSMNameListType,
        related_name='geo_locations',
    )
    start_date_accuracy = graphene.Field(DateAccuracyGrapheneEnum)
    start_date_accuracy_display = EnumDescription(source='get_start_date_accuracy_display')
    end_date_accuracy = graphene.Field(DateAccuracyGrapheneEnum)
    end_date_accuracy_display = EnumDescription(source='get_end_date_accuracy_display')
    category = graphene.Field(FigureCategoryTypeEnum)
    category_display = EnumDescription(source='get_category_display')
    term = graphene.Field(FigureTermsEnum)
    term_display = EnumDescription(source='get_term_display')
    figure_cause = graphene.Field(CrisisTypeGrapheneEnum)
    figure_cause_display = EnumDescription(source='get_figure_cause_display')
    other_sub_type = graphene.Field(OtherSubTypeObjectType)
    figure_typology = graphene.String()
    sources = DjangoPaginatedListObjectField(
        OrganizationListType,
        related_name='sources',
        reverse_related_name='sourced_figures'
    )
    stock_date = graphene.Date()
    stock_reporting_date = graphene.Date()
    flow_start_date = graphene.Date()
    flow_end_date = graphene.Date()
    geolocations = graphene.String()
    sources_reliability = graphene.Field(FigureSourcesReliabilityEnum)
    review_status = graphene.Field(FigureReviewStatusEnum)
    review_status_display = EnumDescription(source='get_review_status_display')
    last_review_comment_status = graphene.List(graphene.NonNull(FigureLastReviewCommentStatusType))

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


class FigureListType(CustomDjangoListObjectType):
    class Meta:
        model = Figure
        filterset_class = FigureFilter


class TotalFigureFilterInputType(graphene.InputObjectType):
    categories = graphene.List(graphene.NonNull(graphene.String))
    filter_figure_start_after = graphene.Date()
    filter_figure_end_before = graphene.Date()
    roles = graphene.List(graphene.NonNull(graphene.String))


class EntryType(DjangoObjectType):
    class Meta:
        model = Entry
        exclude_fields = (
            'reviews', 'figures', 'reviewers', 'review_status', 'review_comments',
            'reviewing',
        )

    created_by = graphene.Field('apps.users.schema.UserType')
    last_modified_by = graphene.Field('apps.users.schema.UserType')
    publishers = DjangoPaginatedListObjectField(
        OrganizationListType,
        related_name='publishers',
        reverse_related_name='published_entries'
    )
    figures = graphene.List(graphene.NonNull(FigureType))

    def resolve_figures(root, info, **kwargs):
        # FIXME: this might be wrong
        return Figure.objects.filter(entry=root.id).select_related(
            'event',
            'violence',
            'violence_sub_type',
            'disaster_category',
            'disaster_sub_category',
            'disaster_type',
            'disaster_sub_type',
            'disaster_category',
            'disaster_sub_category',
            'other_sub_type',
            'osv_sub_type',
            'approved_by',
            'country',
            'event__disaster_category',
            'event__disaster_sub_category',
            'event__disaster_type',
            'event__disaster_sub_type',
            'event__disaster_category',
        ).prefetch_related(
            'tags',
            'context_of_violence',
            'geo_locations',
            'event__disaster_sub_category',
            'event__countries',
            'event__context_of_violence',
            'sources',
            'sources__countries',
            'sources__organization_kind',
        )


class EntryListType(CustomDjangoListObjectType):
    class Meta:
        model = Entry
        filterset_class = EntryExtractionFilterSet


class SourcePreviewType(DjangoObjectType):
    class Meta:
        model = SourcePreview
        exclude_fields = ('entry', 'token')

    status = graphene.Field(PreviewStatusGrapheneEnum)
    status_display = EnumDescription(source='get_status_display')

    def resolve_pdf(root, info, **kwargs):
        if root.status == SourcePreview.PREVIEW_STATUS.COMPLETED:
            return info.context.request.build_absolute_uri(root.pdf.url)
        return None


class VisualizationValueType(ObjectType):
    date = graphene.Date()
    value = graphene.Int()


class VisualizationFigureType(ObjectType):
    idps_conflict_figures = graphene.List(VisualizationValueType, required=False)
    idps_disaster_figures = graphene.List(VisualizationValueType, required=False)
    nds_conflict_figures = graphene.List(VisualizationValueType, required=False)
    nds_disaster_figures = graphene.List(VisualizationValueType, required=False)


class FigureTagListType(CustomDjangoListObjectType):
    class Meta:
        model = FigureTag
        filterset_class = FigureTagFilter


class Query:
    figure_tag = DjangoObjectField(FigureTagType)
    figure_tag_list = DjangoPaginatedListObjectField(FigureTagListType,
                                                     pagination=PageGraphqlPaginationWithoutCount(
                                                         page_size_query_param='pageSize'
                                                     ))

    figure = DjangoObjectField(FigureType)
    figure_list = DjangoPaginatedListObjectField(FigureListType,
                                                 pagination=PageGraphqlPaginationWithoutCount(
                                                     page_size_query_param='pageSize',
                                                 ), filterset_class=FigureExtractionFilterSet)
    source_preview = DjangoObjectField(SourcePreviewType)
    entry = DjangoObjectField(EntryType)
    entry_list = DjangoPaginatedListObjectField(EntryListType,
                                                pagination=PageGraphqlPaginationWithoutCount(
                                                    page_size_query_param='pageSize'
                                                ))
    disaggregated_age = DjangoObjectField(DisaggregatedAgeType)
    figure_aggregations = graphene.Field(
        VisualizationFigureType,
        filters=FigureExtractionFilterDataInputType(required=True),
    )

    @staticmethod
    def resolve_figure_aggregations(_, info, filters):
        # TODO: can we use ReportFigureExtractionFilterSet?
        figure_qs = FigureExtractionFilterSet(data=filters).qs

        idps_conflict_figure_qs = figure_qs.filter(
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT
        ).values('end_date').annotate(value=Sum('total_figures'))

        idps_disaster_figure_qs = figure_qs.filter(
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER
        ).values('end_date').annotate(value=Sum('total_figures'))

        nds_conflict_figure_qs = figure_qs.filter(
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT
        ).values('start_date').annotate(value=Sum('total_figures'))

        nds_disaster_figure_qs = figure_qs.filter(
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER
        ).values('start_date').annotate(value=Sum('total_figures'))

        return VisualizationFigureType(
            idps_conflict_figures=[
                VisualizationValueType(
                    date=k['end_date'],
                    value=k['value']
                ) for k in idps_conflict_figure_qs
            ],
            idps_disaster_figures=[
                VisualizationValueType(
                    date=k['end_date'],
                    value=k['value']
                ) for k in idps_disaster_figure_qs
            ],
            nds_conflict_figures=[
                VisualizationValueType(
                    date=k['start_date'],
                    value=k['value']
                ) for k in nds_conflict_figure_qs
            ],
            nds_disaster_figures=[
                VisualizationValueType(
                    date=k['start_date'],
                    value=k['value']
                ) for k in nds_disaster_figure_qs
            ]

        )
