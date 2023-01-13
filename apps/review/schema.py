import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField
from utils.graphene.enums import EnumDescription

from apps.review.enums import (
    ReviewCommentTypeEnum,
    ReviewFieldTypeEnum,
)
from apps.review.filters import UnifiedReviewCommentFilter
from apps.review.models import UnifiedReviewComment
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.pagination import PageGraphqlPaginationWithoutCount


class UnifiedReviewCommentType(DjangoObjectType):
    comment_type = graphene.NonNull(ReviewCommentTypeEnum)
    comment_display = EnumDescription(source='get_comment_type_display')
    field = graphene.NonNull(ReviewFieldTypeEnum)
    field_display = EnumDescription(source='get_review_field_display')

    class Meta:
        model = UnifiedReviewComment


class UnifiedReviewCommentListType(CustomDjangoListObjectType):
    class Meta:
        model = UnifiedReviewComment
        filterset_class = UnifiedReviewCommentFilter


class Query(object):
    review_comment = DjangoObjectField(UnifiedReviewCommentType)
    review_comments = DjangoPaginatedListObjectField(
        UnifiedReviewCommentListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        )
    )
