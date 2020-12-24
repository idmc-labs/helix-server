import graphene
from django.utils.translation import gettext

from apps.review.enums import ReviewStatusEnum
from apps.review.models import Review, ReviewComment
from apps.review.schema import ReviewCommentType, ReviewType
from apps.review.serializers import ReviewSerializer, ReviewCommentSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker


class ReviewCreateInputType(graphene.InputObjectType):
    # entry is filled from comment
    entry = graphene.ID(required=True)
    figure = graphene.ID(required=False)
    field = graphene.String(required=True)
    value = graphene.NonNull(ReviewStatusEnum)
    age_id = graphene.String(required=False)
    strata_id = graphene.String(required=False)


class ReviewUpdateInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    entry = graphene.ID(required=False)
    figure = graphene.ID(required=False)
    field = graphene.String(required=False)
    value = graphene.NonNull(ReviewStatusEnum)
    age_id = graphene.String(required=False)
    strata_id = graphene.String(required=False)


class CreateReview(graphene.Mutation):
    class Arguments:
        data = ReviewCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ReviewType)

    @staticmethod
    @permission_checker(['review.add_review'])
    def mutate(root, info, data):
        serializer = ReviewSerializer(data=data,
                                      context={'request': info.context})
        if errors := mutation_is_not_valid(serializer):
            return CreateReview(errors=errors, ok=False)
        instance = serializer.save()
        return CreateReview(result=instance, errors=None, ok=True)


class UpdateReview(graphene.Mutation):
    class Arguments:
        data = ReviewUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ReviewType)

    @staticmethod
    @permission_checker(['review.change_review'])
    def mutate(root, info, data):
        try:
            instance = Review.objects.get(id=data['id'])
        except Review.DoesNotExist:
            return UpdateReview(errors=[
                CustomErrorType(field='nonFieldErrors', messages=gettext('Review does not exist.'))
            ])
        serializer = ReviewSerializer(instance=instance, data=data,
                                      context={'request': info.context}, partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateReview(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateReview(result=instance, errors=None, ok=True)


class ReviewCommentCreateInputType(graphene.InputObjectType):
    body = graphene.String(required=False)
    entry = graphene.ID(required=True)
    reviews = graphene.List(ReviewCreateInputType)


class ReviewCommentUpdateInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    body = graphene.String(required=True)


class CreateReviewComment(graphene.Mutation):
    class Arguments:
        data = ReviewCommentCreateInputType(required=True)

    ok = graphene.Boolean()
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    result = graphene.Field(ReviewCommentType)

    @staticmethod
    @permission_checker(['review.add_review'])
    def mutate(root, info, data):
        serializer = ReviewCommentSerializer(
            data=data,
            context={'request': info.context}, partial=True
        )
        if errors := mutation_is_not_valid(serializer):
            return CreateReviewComment(errors=errors, ok=False)
        instance = serializer.save()
        return CreateReviewComment(result=instance, errors=None, ok=True)


class UpdateReviewComment(graphene.Mutation):
    class Arguments:
        data = ReviewCommentUpdateInputType(required=True)

    ok = graphene.Boolean()
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    result = graphene.Field(ReviewCommentType)

    @staticmethod
    @permission_checker(['review.change_review'])
    def mutate(root, info, data):
        try:
            instance = ReviewComment.objects.get(created_by=info.context.user,
                                                 id=data['id'])
        except ReviewComment.DoesNotExist:
            return UpdateReviewComment(
                errors=[
                    dict(field='nonFieldErrors',
                         messages=gettext('Comment does not exist.'))
                ],
                ok=False
            )
        serializer = ReviewCommentSerializer(
            instance=instance,
            data=data,
            context={'request': info.context}, partial=True
        )
        if errors := mutation_is_not_valid(serializer):
            return CreateReviewComment(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateReviewComment(result=instance, errors=None, ok=True)


class DeleteReviewComment(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    result = graphene.Field(ReviewCommentType)

    @staticmethod
    @permission_checker(['review.delete_review'])
    def mutate(root, info, id):
        try:
            instance = ReviewComment.objects.get(created_by=info.context.user,
                                                 id=id)
        except ReviewComment.DoesNotExist:
            return DeleteReviewComment(
                errors=[
                    dict(field='nonFieldErrors',
                         messages=gettext('Comment does not exist.'))
                ],
                ok=False
            )
        instance.delete()
        instance.id = id
        return DeleteReviewComment(result=instance, errors=None, ok=True)


class Mutation(object):
    create_review = CreateReview.Field()
    update_review = UpdateReview.Field()
    create_review_comment = CreateReviewComment.Field()
    update_review_comment = UpdateReviewComment.Field()
    delete_review_comment = DeleteReviewComment.Field()
