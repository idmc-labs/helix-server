import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField
from utils.graphene.enums import EnumDescription

from apps.review.enums import ReviewStatusEnum
from apps.review.filters import ReviewCommentFilter
from apps.review.models import ReviewComment, Review
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.pagination import PageGraphqlPaginationWithoutCount


class ReviewType(DjangoObjectType):
    class Meta:
        model = Review

    value = graphene.NonNull(ReviewStatusEnum)
    value_display = EnumDescription(source='get_value_display')


class ReviewListType(CustomDjangoListObjectType):
    class Meta:
        model = Review
        filter_fields = ('entry',)


class ReviewCommentType(DjangoObjectType):
    class Meta:
        model = ReviewComment

    reviews = DjangoPaginatedListObjectField(ReviewListType)


class ReviewCommentListType(CustomDjangoListObjectType):
    class Meta:
        model = ReviewComment
        filterset_class = ReviewCommentFilter


class Query(object):
    review_list = DjangoPaginatedListObjectField(ReviewListType,
                                                 pagination=PageGraphqlPaginationWithoutCount(
                                                     page_size_query_param='pageSize'
                                                 ))
    review_comment = DjangoObjectField(ReviewCommentType)
    review_comments = DjangoPaginatedListObjectField(ReviewCommentListType,
                                                     pagination=PageGraphqlPaginationWithoutCount(
                                                         page_size_query_param='pageSize'
                                                     ))
