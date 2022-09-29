import graphene
from graphene.types.utils import get_type
from django.contrib.postgres.fields import JSONField
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
    EntryReviewerGrapheneEnum,
    OSMAccuracyGrapheneEnum,
    IdentifierGrapheneEnum,
    FigureCategoryTypeEnum,
    FigureTermsEnum,
    FigureSourcesReliabilityEnum,
)
from apps.entry.filters import EntryReviewerFilter, OSMNameFilter
from apps.entry.models import (
    Figure,
    FigureTag,
    Entry,
    EntryReviewer,
    OSMName,
    DisaggregatedAge,
)
from apps.contrib.models import SourcePreview
from apps.contrib.enums import PreviewStatusGrapheneEnum
from apps.contrib.commons import DateAccuracyGrapheneEnum
from apps.organization.schema import OrganizationListType
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.pagination import PageGraphqlPaginationWithoutCount
from apps.extraction.filters import FigureExtractionFilterSet, EntryExtractionFilterSet
from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.event.schema import OtherSubTypeObjectType


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
        filter_fields = {
            'sex': ('in',),
        }


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


class FigureType(DjangoObjectType):
    class Meta:
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
        DisaggregatedAgeListType, related_name="disaggregation_age"
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


class FigureListType(CustomDjangoListObjectType):
    class Meta:
        model = Figure
        filter_fields = {
            'unit': ('exact',),
            'start_date': ('lte', 'gte'),
        }


class TotalFigureFilterInputType(graphene.InputObjectType):
    categories = graphene.List(graphene.NonNull(graphene.String))
    filter_figure_start_after = graphene.Date()
    filter_figure_end_before = graphene.Date()
    roles = graphene.List(graphene.NonNull(graphene.String))


class EntryType(DjangoObjectType):
    class Meta:
        model = Entry
        exclude_fields = ('reviews', 'figures',)
        filter_fields = ('article_title',)

    created_by = graphene.Field('apps.users.schema.UserType')
    last_modified_by = graphene.Field('apps.users.schema.UserType')
    publishers = DjangoPaginatedListObjectField(OrganizationListType,
                                                related_name='publishers',
                                                reverse_related_name='published_entries')
    latest_reviews = graphene.List('apps.review.schema.ReviewType')
    reviewers = graphene.Dynamic(
        lambda: DjangoPaginatedListObjectField(
            get_type('apps.users.schema.UserListType'),
            related_name='reviewers',
            reverse_related_name='review_entries',
        ))
    review_status = graphene.Field(EntryReviewerGrapheneEnum)
    review_status_display = EnumDescription(source='get_review_status_display')
    review_comments = graphene.Dynamic(
        lambda: DjangoPaginatedListObjectField(
            get_type('apps.review.schema.ReviewCommentListType'),
            pagination=PageGraphqlPaginationWithoutCount(
                page_size_query_param='pageSize'
            )
        )
    )
    # total_stock_idp_figures = graphene.Field(graphene.Int,
    #                                          data=TotalFigureFilterInputType())
    # total_flow_nd_figures = graphene.Field(graphene.Int,
    #                                        data=TotalFigureFilterInputType())
    is_reviewed = graphene.NonNull(graphene.Boolean, deprecation_reason='Please use `reviewStatus` field.')
    is_under_review = graphene.NonNull(graphene.Boolean, deprecation_reason='Please use `reviewStatus` field.')
    is_signed_off = graphene.NonNull(graphene.Boolean, deprecation_reason='Please use `reviewStatus` field.')
    figures = graphene.List(graphene.NonNull(FigureType))

    # def resolve_total_stock_idp_figures(root, info, **kwargs):
    #     NULL = 'null'
    #     value = getattr(
    #         root,
    #         Entry.IDP_FIGURES_ANNOTATE,
    #         NULL
    #     )
    #     if value != NULL:
    #         return value
    #     return info.context.entry_entry_total_stock_idp_figures.load(root.id)
    #
    # def resolve_total_flow_nd_figures(root, info, **kwargs):
    #     NULL = 'null'
    #     value = getattr(
    #         root,
    #         Entry.ND_FIGURES_ANNOTATE,
    #         NULL
    #     )
    #     if value != NULL:
    #         return value
    #     return info.context.entry_entry_total_flow_nd_figures.load(root.id)
    def resolve_figures(root, info, **kwargs):
        return Figure.objects.filter(entry=root.id)


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


class EntryReviewerType(DjangoObjectType):
    class Meta:
        model = EntryReviewer

    status = graphene.Field(EntryReviewerGrapheneEnum)
    status_display = EnumDescription(source='get_status_display')


class EntryReviewerListType(CustomDjangoListObjectType):
    class Meta:
        model = EntryReviewer
        filterset_class = EntryReviewerFilter


class FigureTagListType(CustomDjangoListObjectType):
    class Meta:
        model = FigureTag
        filter_fields = {
            'name': ('unaccent__icontains',),
        }


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
    disaggregated_age_list = DjangoPaginatedListObjectField(DisaggregatedAgeListType)
