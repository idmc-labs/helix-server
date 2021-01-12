import graphene
from graphene.types.utils import get_type
from django.contrib.postgres.fields import JSONField
from graphene import ObjectType
from graphene.types.generic import GenericScalar
from graphene_django import DjangoObjectType
from graphene_django_extras.converter import convert_django_field
from graphene_django_extras import PageGraphqlPagination, DjangoObjectField
import logging

from apps.entry.enums import (
    QuantifierGrapheneEnum,
    UnitGrapheneEnum,
    TermGrapheneEnum,
    RoleGrapheneEnum,
    EntryReviewerGrapheneEnum,
    OSMAccuracyGrapheneEnum,
    IdentifierGrapheneEnum,
)
from apps.entry.filters import EntryFilter, EntryReviewerFilter, OSMNameFilter
from apps.entry.models import (
    Figure,
    FigureTag,
    Entry,
    SourcePreview,
    EntryReviewer,
    FigureCategory,
    OSMName,
)
from apps.organization.schema import OrganizationListType
from utils.fields import (
    DjangoPaginatedListObjectField,
    CustomDjangoListObjectType,
)

logger = logging.getLogger(__name__)


@convert_django_field.register(JSONField)
def convert_json_field_to_scalar(field, registry=None):
    # https://github.com/graphql-python/graphene-django/issues/303#issuecomment-339939955
    return GenericScalar()


class DisaggregatedAgeType(ObjectType):
    uuid = graphene.String(required=True)
    age_from = graphene.Int()
    age_to = graphene.Int()
    value = graphene.Int()


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


class FigureCategoryObjectType(DjangoObjectType):
    class Meta:
        model = FigureCategory


class FigureCategoryListType(CustomDjangoListObjectType):
    class Meta:
        model = FigureCategory
        filter_fields = {
            'name': ('icontains',),
        }


class FigureType(DjangoObjectType):
    class Meta:
        model = Figure

    quantifier = graphene.Field(QuantifierGrapheneEnum)
    unit = graphene.Field(UnitGrapheneEnum)
    term = graphene.Field(TermGrapheneEnum)
    role = graphene.Field(RoleGrapheneEnum)
    age_json = graphene.List(graphene.NonNull(DisaggregatedAgeType))
    strata_json = graphene.List(graphene.NonNull(DisaggregatedStratumType))
    geo_locations = DjangoPaginatedListObjectField(OSMNameListType, accessor='geo_locations')


class FigureListType(CustomDjangoListObjectType):
    class Meta:
        model = Figure
        filter_fields = {
            'unit': ('exact',),
            'start_date': ('lte', 'gte'),
        }


class EntryType(DjangoObjectType):
    class Meta:
        model = Entry
        exclude_fields = ('reviews',)

    created_by = graphene.Field('apps.users.schema.UserType')
    last_modified_by = graphene.Field('apps.users.schema.UserType')
    sources = DjangoPaginatedListObjectField(OrganizationListType,
                                             accessor='sources')
    publishers = DjangoPaginatedListObjectField(OrganizationListType,
                                                accessor='publishers')
    figures = DjangoPaginatedListObjectField(FigureListType,
                                             pagination=PageGraphqlPagination(
                                                 page_size_query_param='perPage'
                                             ))
    latest_reviews = graphene.List('apps.review.schema.ReviewType')
    reviewers = graphene.Dynamic(
        lambda: DjangoPaginatedListObjectField(
            get_type('apps.users.schema.UserListType'),
            accessor='reviewers'
        ))
    review_comments = graphene.Dynamic(
        lambda: DjangoPaginatedListObjectField(
            get_type('apps.review.schema.ReviewCommentListType'),
            accessor='review_comments',
            pagination=PageGraphqlPagination(
                page_size_query_param='pageSize'
            )
        )
    )
    total_figures = graphene.Field(graphene.Int)
    source_methodology = graphene.Field(graphene.String)


class EntryListType(CustomDjangoListObjectType):
    class Meta:
        model = Entry
        filterset_class = EntryFilter


class SourcePreviewType(DjangoObjectType):
    class Meta:
        model = SourcePreview
        exclude_fields = ('entry', 'token')

    def resolve_pdf(root, info, **kwargs):
        return root.pdf.url


class EntryReviewerType(DjangoObjectType):
    class Meta:
        model = EntryReviewer

    status = graphene.Field(EntryReviewerGrapheneEnum)


class EntryReviewerListType(CustomDjangoListObjectType):
    class Meta:
        model = EntryReviewer
        filterset_class = EntryReviewerFilter


class FigureTagType(DjangoObjectType):
    class Meta:
        model = FigureTag
        exclude_fields = ('entry_set',)


class FigureTagListType(CustomDjangoListObjectType):
    class Meta:
        model = FigureTag
        filter_fields = {
            'name': ('icontains',),
        }


class Query:
    figure_category = DjangoObjectField(FigureCategoryObjectType)
    figure_category_list = DjangoPaginatedListObjectField(FigureCategoryListType)
    figure_tag = DjangoObjectField(FigureTagType)
    figure_tag_list = DjangoPaginatedListObjectField(FigureTagListType)

    figure = DjangoObjectField(FigureType)
    figure_list = DjangoPaginatedListObjectField(FigureListType,
                                                 pagination=PageGraphqlPagination(
                                                     page_size_query_param='pageSize'
                                                 ))
    source_preview = DjangoObjectField(SourcePreviewType)
    entry = DjangoObjectField(EntryType)
    entry_list = DjangoPaginatedListObjectField(EntryListType,
                                                pagination=PageGraphqlPagination(
                                                    page_size_query_param='pageSize'
                                                ))
