import graphene
from django.utils.translation import gettext

from apps.review.models import UnifiedReviewComment
from apps.review.schema import UnifiedReviewCommentType
from apps.review.serializers import UnifiedReviewCommentSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker
from utils.mutation import generate_input_type_for_serializer


UnifiedReviewCommentCreateInputType = generate_input_type_for_serializer(
    'UnifiedReviewCommentCreateInputType',
    UnifiedReviewCommentSerializer
)


class UnifiedReviewCommentUpdateInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    comment = graphene.String(required=True)


class CreateUnifiedReviewComment(graphene.Mutation):
    class Arguments:
        data = UnifiedReviewCommentCreateInputType(required=True)

    ok = graphene.Boolean()
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    result = graphene.Field(UnifiedReviewCommentType)

    @staticmethod
    @permission_checker(['review.add_reviewcomment'])
    def mutate(root, info, data):
        serializer = UnifiedReviewCommentSerializer(
            data=data,
            context={'request': info.context.request}, partial=True
        )
        if serializer.is_valid():
            serialized_data = serializer.validated_data
            review_comment = serialized_data.get('comment_type')
            event = serialized_data.get('event')
            if (
                event and
                review_comment != UnifiedReviewComment.REVIEW_COMMENT_TYPE.GREY and
                (not event.assignee or event.assignee != info.context.user)
            ):
                return UpdateUnifiedReviewComment(
                    errors=[
                        dict(field='nonFieldErrors',
                             messages=gettext('Assignee not set or you are not the assignee.'))
                    ],
                    ok=False
                )

        if errors := mutation_is_not_valid(serializer):
            return CreateUnifiedReviewComment(errors=errors, ok=False)

        instance = serializer.save()
        return CreateUnifiedReviewComment(result=instance, errors=None, ok=True)


class UpdateUnifiedReviewComment(graphene.Mutation):
    class Arguments:
        data = UnifiedReviewCommentUpdateInputType(required=True)

    ok = graphene.Boolean()
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    result = graphene.Field(UnifiedReviewCommentType)

    @staticmethod
    @permission_checker(['review.change_reviewcomment'])
    def mutate(root, info, data):
        try:
            instance = UnifiedReviewComment.objects.get(created_by=info.context.user, id=data['id'])
        except UnifiedReviewComment.DoesNotExist:
            return UpdateUnifiedReviewComment(
                errors=[
                    dict(field='nonFieldErrors',
                         messages=gettext('Comment does not exist.'))
                ],
                ok=False
            )
        data['is_edited'] = True
        serializer = UnifiedReviewCommentSerializer(
            instance=instance,
            data=data,
            context={'request': info.context.request}, partial=True
        )
        if errors := mutation_is_not_valid(serializer):
            return UpdateUnifiedReviewComment(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateUnifiedReviewComment(result=instance, errors=None, ok=True)


class DeleteUnifiedReviewComment(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    result = graphene.Field(UnifiedReviewCommentType)

    @staticmethod
    @permission_checker(['review.delete_reviewcomment'])
    def mutate(root, info, id):
        try:
            instance = UnifiedReviewComment.objects.get(
                created_by=info.context.user,
                id=id
            )
        except UnifiedReviewComment.DoesNotExist:
            return DeleteUnifiedReviewComment(
                errors=[
                    dict(field='nonFieldErrors',
                         messages=gettext('Comment does not exist.'))
                ],
                ok=False
            )
        instance.is_deleted = True
        instance.comment = None
        instance.save()
        return DeleteUnifiedReviewComment(result=instance, errors=None, ok=True)


class Mutation(object):
    create_review_comment = CreateUnifiedReviewComment.Field()
    update_review_comment = UpdateUnifiedReviewComment.Field()
    delete_review_comment = DeleteUnifiedReviewComment.Field()
