from django.utils.translation import gettext
import graphene

from apps.contrib.models import SourcePreview
from apps.entry.enums import (
    EntryReviewerGrapheneEnum,
)
from apps.entry.models import Entry, EntryReviewer, FigureTag
from apps.entry.schema import (
    EntryType,
    SourcePreviewType,
    EntryReviewerType,
    FigureTagType,)
from apps.entry.serializers import (
    EntryCreateSerializer,
    EntryUpdateSerializer,
    FigureTagCreateSerializer,
    FigureTagUpdateSerializer,
)
from apps.contrib.serializers import SourcePreviewSerializer
from apps.users.roles import USER_ROLE
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker, is_authenticated
from utils.mutation import generate_input_type_for_serializer

# entry

EntryCreateInputType = generate_input_type_for_serializer(
    'EntryCreateInputType',
    serializer_class=EntryCreateSerializer
)

EntryUpdateInputType = generate_input_type_for_serializer(
    'EntryUpdateInputType',
    serializer_class=EntryUpdateSerializer,
)


class CreateEntry(graphene.Mutation):
    class Arguments:
        data = EntryCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(EntryType)

    @staticmethod
    @permission_checker(['entry.add_entry'])
    def mutate(root, info, data):
        serializer = EntryCreateSerializer(data=data, context={'request': info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return CreateEntry(errors=errors, ok=False)
        instance = serializer.save()
        return CreateEntry(result=instance, errors=None, ok=True)


class UpdateEntry(graphene.Mutation):
    class Arguments:
        data = EntryUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(EntryType)

    @staticmethod
    @permission_checker(['entry.change_entry'])
    def mutate(root, info, data):
        try:
            instance = Entry.objects.get(id=data['id'])
        except Entry.DoesNotExist:
            return UpdateEntry(errors=[
                dict(field='nonFieldErrors', messages=gettext('Entry does not exist.'))
            ])
        if not instance.can_be_updated_by(info.context.user):
            return UpdateEntry(errors=[
                dict(field='nonFieldErrors', messages=gettext('You cannot update this entry.'))
            ])
        serializer = EntryUpdateSerializer(instance=instance, data=data,
                                           context={'request': info.context.request}, partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateEntry(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateEntry(result=instance, errors=None, ok=True)


class DeleteEntry(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(EntryType)

    @staticmethod
    @permission_checker(['entry.delete_entry'])
    def mutate(root, info, id):
        try:
            instance = Entry.objects.get(id=id)
        except Entry.DoesNotExist:
            return DeleteEntry(errors=[
                dict(field='nonFieldErrors', messages=gettext('Entry does not exist.'))
            ])
        if not instance.can_be_updated_by(info.context.user):
            return DeleteEntry(errors=[
                dict(field='nonFieldErrors', messages=gettext('You cannot delete this entry.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteEntry(result=instance, errors=None, ok=True)


# source preview


SourcePreviewInputType = generate_input_type_for_serializer(
    'SourcePreviewInputType',
    SourcePreviewSerializer
)


class CreateSourcePreview(graphene.Mutation):
    """
    Pass id if you accidentally posted a wrong url, and need to change the preview.
    """

    class Arguments:
        data = SourcePreviewInputType(required=True)

    ok = graphene.Boolean()
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    result = graphene.Field(SourcePreviewType)

    @staticmethod
    @permission_checker(['entry.add_entry'])
    def mutate(root, info, data):
        if data.get('id'):
            try:
                instance = SourcePreview.objects.get(id=data['id'])
                serializer = SourcePreviewSerializer(data=data, instance=instance,
                                                     context={'request': info.context.request})
            except SourcePreview.DoesNotExist:
                return CreateSourcePreview(errors=[
                    dict(field='nonFieldErrors', messages=gettext('Preview does not exist.'))
                ])
        else:
            serializer = SourcePreviewSerializer(data=data,
                                                 context={'request': info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return CreateSourcePreview(errors=errors, ok=False)
        instance = serializer.save()
        return CreateSourcePreview(result=instance, errors=None, ok=True)


# Entry review


class EntryReviewStatusInputType(graphene.InputObjectType):
    entry = graphene.ID(required=True)
    status = graphene.Field(EntryReviewerGrapheneEnum, required=True)


class UpdateEntryReview(graphene.Mutation):
    class Arguments:
        data = EntryReviewStatusInputType(required=True)

    ok = graphene.Boolean()
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    result = graphene.Field(EntryReviewerType)

    @staticmethod
    @is_authenticated()
    def mutate(root, info, data):
        reviewer = info.context.user
        try:
            entry = Entry.objects.get(id=data['entry'])
        except Entry.DoesNotExist:
            return UpdateEntryReview(errors=[
                dict(field='nonFieldErrors', messages=gettext('Entry does not exist.'))
            ])
        try:
            entry_review = EntryReviewer.objects.get(entry=entry, reviewer=reviewer)
            entry_review.status = data['status']
            entry_review.save()
        except EntryReviewer.DoesNotExist:
            signed_off_status = EntryReviewer.REVIEW_STATUS.SIGNED_OFF
            if reviewer.role == USER_ROLE.IT_HEAD.value and data['status'] == signed_off_status:
                entry_review = EntryReviewer.objects.create(entry=entry, reviewer=reviewer, status=signed_off_status)
            else:
                return UpdateEntryReview(errors=[
                    dict(field='nonFieldErrors', messages=gettext('Review not found.'))
                ])
        except EntryReviewer.CannotUpdateStatusException as e:
            return UpdateEntryReview(errors=[
                dict(field='nonFieldErrors', messages=gettext(e.message))
            ])
        return CreateSourcePreview(errors=None, ok=True, result=entry_review)


# Figure Tag


FigureTagCreateInputType = generate_input_type_for_serializer(
    'FigureTagCreateInputType',
    FigureTagCreateSerializer
)


FigureTagUpdateInputType = generate_input_type_for_serializer(
    'FigureTagUpdateInputType',
    FigureTagUpdateSerializer
)


class CreateFigureTag(graphene.Mutation):
    class Arguments:
        data = FigureTagCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(FigureTagType)

    @staticmethod
    @is_authenticated()
    def mutate(root, info, data):
        serializer = FigureTagCreateSerializer(data=data, context={'request': info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return CreateFigureTag(errors=errors, ok=False)
        instance = serializer.save()
        return CreateFigureTag(result=instance, errors=None, ok=True)


class UpdateFigureTag(graphene.Mutation):
    class Arguments:
        data = FigureTagUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(FigureTagType)

    @staticmethod
    @is_authenticated()
    def mutate(root, info, data):
        try:
            instance = FigureTag.objects.get(id=data['id'])
        except FigureTag.DoesNotExist:
            return UpdateFigureTag(errors=[
                dict(field='nonFieldErrors', messages=gettext('Tag does not exist.'))
            ])
        serializer = FigureTagCreateSerializer(instance=instance, data=data,
                                               context={'request': info.context.request}, partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateFigureTag(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateFigureTag(result=instance, errors=None, ok=True)


class DeleteFigureTag(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(FigureTagType)

    @staticmethod
    @is_authenticated()
    def mutate(root, info, id):
        try:
            instance = FigureTag.objects.get(id=id)
        except FigureTag.DoesNotExist:
            return DeleteFigureTag(errors=[
                dict(field='nonFieldErrors', messages=gettext('Tag does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteFigureTag(result=instance, errors=None, ok=True)


class Mutation(object):
    create_entry = CreateEntry.Field()
    update_entry = UpdateEntry.Field()
    delete_entry = DeleteEntry.Field()
    create_source_preview = CreateSourcePreview.Field()
    # entry review
    update_entry_review = UpdateEntryReview.Field()
    # figure tags
    create_figure_tag = CreateFigureTag.Field()
    update_figure_tag = UpdateFigureTag.Field()
    delete_figure_tag = DeleteFigureTag.Field()
