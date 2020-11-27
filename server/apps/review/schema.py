from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField, PageGraphqlPagination

from apps.review.models import ReviewComment, Review
from utils.fields import CustomDjangoListObjectType, DjangoPaginatedListObjectField


class ReviewType(DjangoObjectType):
    class Meta:
        model = Review


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
        filter_fields = ('entry',)


class Query(object):
    review_list = DjangoPaginatedListObjectField(ReviewListType,
                                                 pagination=PageGraphqlPagination(
                                                     page_size_query_param='pageSize'
                                                 ))
    review_comments = DjangoPaginatedListObjectField(ReviewCommentListType,
                                                     pagination=PageGraphqlPagination(
                                                         page_size_query_param='pageSize'
                                                     ))
