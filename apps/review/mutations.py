import graphene
from django.utils.translation import gettext

from apps.review.models import ReviewComment
from apps.review.schema import ReviewCommentType
from apps.review.serializers import ReviewCommentSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker
from utils.mutation import generate_input_type_for_serializer


ReviewCommentCreateInputType = generate_input_type_for_serializer(
    'ReviewCommentCreateInputType',
    ReviewCommentSerializer
)


class CommentCreateInputType(graphene.InputObjectType):
    body = graphene.String(required=False)
    entry = graphene.ID(required=True)


class CommentUpdateInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    body = graphene.String(required=True)


class CreateComment(graphene.Mutation):
    class Arguments:
        data = CommentCreateInputType(required=True)

    ok = graphene.Boolean()
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    result = graphene.Field(ReviewCommentType)

    @staticmethod
    @permission_checker(['review.add_reviewcomment'])
    def mutate(root, info, data):
        serializer = ReviewCommentSerializer(
            data=data,
            context={'request': info.context.request}, partial=True
        )
        if errors := mutation_is_not_valid(serializer):
            return CreateComment(errors=errors, ok=False)
        instance = serializer.save()
        return CreateComment(result=instance, errors=None, ok=True)


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
            context={'request': info.context.request}, partial=True
        )
        if errors := mutation_is_not_valid(serializer):
            return CreateReviewComment(errors=errors, ok=False)
        instance = serializer.save()
        return CreateReviewComment(result=instance, errors=None, ok=True)


class UpdateComment(graphene.Mutation):
    class Arguments:
        data = CommentUpdateInputType(required=True)

    ok = graphene.Boolean()
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    result = graphene.Field(ReviewCommentType)

    @staticmethod
    @permission_checker(['review.change_reviewcomment'])
    def mutate(root, info, data):
        try:
            instance = ReviewComment.objects.get(created_by=info.context.user,
                                                 id=data['id'])
        except ReviewComment.DoesNotExist:
            return UpdateComment(
                errors=[
                    dict(field='nonFieldErrors',
                         messages=gettext('Comment does not exist.'))
                ],
                ok=False
            )
        serializer = ReviewCommentSerializer(
            instance=instance,
            data=data,
            context={'request': info.context.request}, partial=True
        )
        if errors := mutation_is_not_valid(serializer):
            return UpdateComment(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateComment(result=instance, errors=None, ok=True)


class DeleteReviewComment(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    result = graphene.Field(ReviewCommentType)

    @staticmethod
    @permission_checker(['review.delete_reviewcomment'])
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
    create_comment = CreateComment.Field()
    create_review_comment = CreateReviewComment.Field()
    update_comment = UpdateComment.Field()
    delete_review_comment = DeleteReviewComment.Field()
