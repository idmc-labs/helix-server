import graphene
from graphene.types.utils import get_type
from django.contrib.postgres.fields import JSONField
from graphene import ObjectType
from graphene.types.generic import GenericScalar
from graphene_django import DjangoObjectType
from graphene_django_extras.converter import convert_django_field
from graphene_django_extras import DjangoObjectField
import logging

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
)
from apps.entry.filters import EntryReviewerFilter, OSMNameFilter
from apps.entry.models import (
    Figure,
    FigureTag,
    Entry,
    EntryReviewer,
    OSMName,
    DisaggregatedAgeCategory,
    DisaggregatedAge,
)
from apps.contrib.models import SourcePreview
from apps.contrib.enums import PreviewStatusGrapheneEnum
from apps.contrib.commons import DateAccuracyGrapheneEnum
from apps.organization.schema import OrganizationListType
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.pagination import PageGraphqlPaginationWithoutCount
from apps.extraction.filters import BaseFigureExtractionFilterSet, EntryExtractionFilterSet
from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.event.enums import EventOtherSubTypeEnum


logger = logging.getLogger(__name__)


@convert_django_field.register(JSONField)
def convert_json_field_to_scalar(field, registry=None):
    # https://github.com/graphql-python/graphene-django/issues/303#issuecomment-339939955
    return GenericScalar()


class DisaggregatedAgeCategoryType(DjangoObjectType):
    class Meta:
        model = DisaggregatedAgeCategory


class DisaggregatedAgeCategoryListType(CustomDjangoListObjectType):
    class Meta:
        model = DisaggregatedAgeCategory
        filter_fields = {
            'name': ('unaccent__icontains',),
        }


class DisaggregatedAgeType(DjangoObjectType):
    class Meta:
        model = DisaggregatedAge
    uuid = graphene.String(required=True)
    category = graphene.Field(DisaggregatedAgeCategoryType)
    sex = graphene.Field(GenderTypeGrapheneEnum)

    def resolve_category(root, info):
        return DisaggregatedAgeCategory.objects.filter(id=root.category.id).first()


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
    identifier = graphene.Field(IdentifierGrapheneEnum)


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
    unit = graphene.Field(UnitGrapheneEnum)
    role = graphene.Field(RoleGrapheneEnum)
    displacement_occurred = graphene.Field(DisplacementOccurredGrapheneEnum)
    disaggregation_age = DjangoPaginatedListObjectField(
        DisaggregatedAgeListType, related_name="disaggregation_age"
    )
    disaggregation_strata_json = graphene.List(graphene.NonNull(DisaggregatedStratumType))
    geo_locations = DjangoPaginatedListObjectField(
        OSMNameListType,
        related_name='geo_locations',
    )
    start_date_accuracy = graphene.Field(DateAccuracyGrapheneEnum)
    end_date_accuracy = graphene.Field(DateAccuracyGrapheneEnum)
    category = graphene.Field(FigureCategoryTypeEnum)
    term = graphene.Field(FigureTermsEnum)
    figure_cause = graphene.Field(CrisisTypeGrapheneEnum)
    other_sub_type = figure_cause = graphene.Field(EventOtherSubTypeEnum)


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
        exclude_fields = ('reviews',)
        filter_fields = ('article_title',)

    created_by = graphene.Field('apps.users.schema.UserType')
    last_modified_by = graphene.Field('apps.users.schema.UserType')
    sources = DjangoPaginatedListObjectField(OrganizationListType,
                                             related_name='sources',
                                             reverse_related_name='sourced_entries')
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
    review_comments = graphene.Dynamic(
        lambda: DjangoPaginatedListObjectField(
            get_type('apps.review.schema.ReviewCommentListType'),
            pagination=PageGraphqlPaginationWithoutCount(
                page_size_query_param='pageSize'
            )
        )
    )
    total_stock_idp_figures = graphene.Field(graphene.Int,
                                             data=TotalFigureFilterInputType())
    total_flow_nd_figures = graphene.Field(graphene.Int,
                                           data=TotalFigureFilterInputType())
    source_methodology = graphene.Field(graphene.String)
    is_reviewed = graphene.NonNull(graphene.Boolean, deprecation_reason='Please use `reviewStatus` field.')
    is_under_review = graphene.NonNull(graphene.Boolean, deprecation_reason='Please use `reviewStatus` field.')
    is_signed_off = graphene.NonNull(graphene.Boolean, deprecation_reason='Please use `reviewStatus` field.')

    def resolve_total_stock_idp_figures(root, info, **kwargs):
        NULL = 'null'
        value = getattr(
            root,
            Entry.IDP_FIGURES_ANNOTATE,
            NULL
        )
        if value != NULL:
            return value
        return info.context.entry_entry_total_stock_idp_figures.load(root.id)

    def resolve_total_flow_nd_figures(root, info, **kwargs):
        NULL = 'null'
        value = getattr(
            root,
            Entry.ND_FIGURES_ANNOTATE,
            NULL
        )
        if value != NULL:
            return value
        return info.context.entry_entry_total_flow_nd_figures.load(root.id)


class EntryListType(CustomDjangoListObjectType):
    class Meta:
        model = Entry
        filterset_class = EntryExtractionFilterSet


class SourcePreviewType(DjangoObjectType):
    class Meta:
        model = SourcePreview
        exclude_fields = ('entry', 'token')

    status = graphene.Field(PreviewStatusGrapheneEnum)

    def resolve_pdf(root, info, **kwargs):
        if root.status == SourcePreview.PREVIEW_STATUS.COMPLETED:
            return info.context.request.build_absolute_uri(root.pdf.url)
        return None


class EntryReviewerType(DjangoObjectType):
    class Meta:
        model = EntryReviewer

    status = graphene.Field(EntryReviewerGrapheneEnum)


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
                                                 ), filterset_class=BaseFigureExtractionFilterSet)
    source_preview = DjangoObjectField(SourcePreviewType)
    entry = DjangoObjectField(EntryType)
    entry_list = DjangoPaginatedListObjectField(EntryListType,
                                                pagination=PageGraphqlPaginationWithoutCount(
                                                    page_size_query_param='pageSize'
                                                ))
    disaggregated_age_category = DjangoObjectField(DisaggregatedAgeCategoryType)
    disaggregated_age_category_list = DjangoPaginatedListObjectField(DisaggregatedAgeCategoryListType)
    disaggregated_age = DjangoObjectField(DisaggregatedAgeType)
    disaggregated_age_list = DjangoPaginatedListObjectField(DisaggregatedAgeListType)
