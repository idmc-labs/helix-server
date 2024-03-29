from django.utils.translation import gettext
import graphene
from django.utils import timezone
from django.db import transaction

from apps.entry.models import Entry, FigureTag, Figure
from apps.entry.schema import (
    EntryType,
    FigureType,
    SourcePreviewType,
    FigureTagType,)
from apps.entry.serializers import (
    EntryCreateSerializer,
    EntryUpdateSerializer,
    FigureTagCreateSerializer,
    FigureTagUpdateSerializer,
    FigureSerializer,
)
from apps.extraction.filters import FigureExtractionFilterDataInputType, EntryExtractionFilterDataInputType
from apps.contrib.models import SourcePreview, ExcelDownload
from apps.contrib.mutations import ExportBaseMutation
from apps.contrib.serializers import SourcePreviewSerializer
from apps.extraction.filters import FigureTagFilterDataInputType
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker, is_authenticated
from utils.mutation import generate_input_type_for_serializer, BulkUpdateMutation

from apps.notification.models import Notification
from .utils import BulkUpdateFigureManager, send_figure_notifications, get_figure_notification_type

# entry

EntryCreateInputType = generate_input_type_for_serializer(
    'EntryCreateInputType',
    serializer_class=EntryCreateSerializer
)

EntryUpdateInputType = generate_input_type_for_serializer(
    'EntryUpdateInputType',
    serializer_class=EntryUpdateSerializer,
)

FigureUpdateInputType = generate_input_type_for_serializer(
    'FigureUpdateInputType',
    serializer_class=FigureSerializer,
    partial=True,
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
        from apps.event.models import Event

        try:
            instance = Entry.objects.get(id=id)
        except Entry.DoesNotExist:
            return DeleteEntry(errors=[
                dict(field='nonFieldErrors', messages=gettext('Entry does not exist.'))
            ])

        affected_event_ids = []

        # Send notification to regional co-ordinators
        # TODO: Can we re-use the function defined on DeleteFigure._get_notification_type?
        for review_status in [
            Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED,
            Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED,
            Event.EVENT_REVIEW_STATUS.APPROVED,
            Event.EVENT_REVIEW_STATUS.SIGNED_OFF,
        ]:
            figures = instance.figures.filter(
                entry__id=instance.id,
                event__review_status=review_status
            )

            for figure in figures:
                recipients = [
                    user['id'] for user in Event.regional_coordinators(
                        event=figure.event,
                        actor=info.context.user,
                    )
                ]
                if figure.event.created_by_id:
                    recipients.append(figure.event.created_by_id)
                if figure.event.assignee_id:
                    recipients.append(figure.event.assignee_id)

                notification_type = Notification.Type.FIGURE_DELETED_IN_APPROVED_EVENT
                if (
                    review_status == Event.EVENT_REVIEW_STATUS.SIGNED_OFF or
                    review_status == Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED
                ):
                    notification_type = Notification.Type.FIGURE_DELETED_IN_SIGNED_EVENT

                Notification.send_safe_multiple_notifications(
                    recipients=recipients,
                    actor=info.context.user,
                    type=notification_type,
                    event=figure.event,
                    text=gettext('Entry and figures were deleted'),
                )

                affected_event_ids.append(figure.event_id)

        for event_id in list(set(affected_event_ids)):
            Figure.update_event_status_and_send_notifications(event_id)

        instance.delete()

        instance.id = id
        return DeleteEntry(result=instance, errors=None, ok=True)


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
    @permission_checker(['entry.add_figuretag'])
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
    @permission_checker(['entry.change_figuretag'])
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
    @permission_checker(['entry.delete_figuretag'])
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


class ExportEntries(ExportBaseMutation):
    class Arguments(ExportBaseMutation.Arguments):
        filters = EntryExtractionFilterDataInputType(required=True)
    DOWNLOAD_TYPE = ExcelDownload.DOWNLOAD_TYPES.ENTRY


class ExportFigures(ExportBaseMutation):
    class Arguments(ExportBaseMutation.Arguments):
        # TODO: use Can we use ReportFigureExtractionFilterSet?
        filters = FigureExtractionFilterDataInputType(required=True)

    DOWNLOAD_TYPE = ExcelDownload.DOWNLOAD_TYPES.FIGURE


class ExportFigureTags(ExportBaseMutation):
    """
    Mutation to figure tags data based on provided filters.
    """
    class Arguments(ExportBaseMutation.Arguments):
        filters = FigureTagFilterDataInputType(required=True)
    DOWNLOAD_TYPE = ExcelDownload.DOWNLOAD_TYPES.FIGURE_TAG


class DeleteFigure(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(FigureType)

    @staticmethod
    @permission_checker(['entry.delete_figure'])
    def mutate(root, info, id):
        from apps.event.models import Event

        try:
            instance = Figure.objects.get(id=id)
        except Entry.DoesNotExist:
            return DeleteFigure(errors=[
                dict(field='nonFieldErrors', messages=gettext('Figure does not exist.'))
            ])

        instance.delete()

        def _get_notification_type(event):
            if event.review_status in [
                Event.EVENT_REVIEW_STATUS.APPROVED,
                Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED,
            ]:
                return Notification.Type.FIGURE_DELETED_IN_APPROVED_EVENT
            if event.review_status in [
                Event.EVENT_REVIEW_STATUS.SIGNED_OFF,
                Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED,
            ]:
                return Notification.Type.FIGURE_DELETED_IN_SIGNED_EVENT
            return None

        _type = _get_notification_type(instance.event)

        if _type:
            recipients = [user['id'] for user in Event.regional_coordinators(
                instance.event,
                actor=info.context.user,
            )]
            if instance.event.created_by_id:
                recipients.append(instance.event.created_by_id)
            if instance.event.assignee_id:
                recipients.append(instance.event.assignee_id)

            Notification.send_safe_multiple_notifications(
                recipients=recipients,
                actor=info.context.user,
                type=_type,
                entry=instance.entry,
                event=instance.event,
            )

        Figure.update_event_status_and_send_notifications(instance.event_id)
        instance.event.refresh_from_db()

        return DeleteFigure(errors=None, ok=True)


class ApproveFigure(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(FigureType)

    @staticmethod
    @permission_checker(['entry.approve_figure'])
    def mutate(root, info, id):
        figure = Figure.objects.filter(id=id).first()
        if not figure:
            return ApproveFigure(errors=[
                dict(field='nonFieldErrors', messages=gettext('Figure does not exist.'))
            ])
        if figure.review_status == Figure.FIGURE_REVIEW_STATUS.APPROVED:
            return ApproveFigure(errors=[
                dict(field='nonFieldErrors', messages=gettext('Approved figures cannot be approved'))
            ])

        figure.review_status = Figure.FIGURE_REVIEW_STATUS.APPROVED
        figure.approved_by = info.context.user
        figure.approved_on = timezone.now()
        figure.save()

        # NOTE: not sending notification when figure is approved as it is not actionable

        Figure.update_event_status_and_send_notifications(figure.event_id)
        figure.event.refresh_from_db()

        return ApproveFigure(result=figure, errors=None, ok=True)


class UnapproveFigure(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(FigureType)

    @staticmethod
    @permission_checker(['entry.approve_figure'])
    @is_authenticated()
    def mutate(root, info, id):
        from apps.event.models import Event
        figure = Figure.objects.filter(id=id).first()
        if not figure:
            return UnapproveFigure(errors=[
                dict(field='nonFieldErrors', messages=gettext('Figure does not exist.'))
            ])
        if figure.review_status != Figure.FIGURE_REVIEW_STATUS.APPROVED:
            return UnapproveFigure(errors=[
                dict(field='nonFieldErrors', messages=gettext('Only approved figures can be un-approved'))
            ])

        figure.review_status = (
            Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS
            if figure.figure_review_comments.all().count() > 0
            else Figure.FIGURE_REVIEW_STATUS.REVIEW_NOT_STARTED
        )
        figure.approved_by = None
        figure.approved_on = None
        figure.save()

        def _get_notification_type(event):
            if event.review_status in [
                Event.EVENT_REVIEW_STATUS.APPROVED,
                Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED,
            ]:
                return Notification.Type.FIGURE_UNAPPROVED_IN_APPROVED_EVENT
            if event.review_status in [
                Event.EVENT_REVIEW_STATUS.SIGNED_OFF,
                Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED,
            ]:
                return Notification.Type.FIGURE_UNAPPROVED_IN_SIGNED_EVENT
            return None

        _type = _get_notification_type(figure.event)
        if _type:
            recipients = [user['id'] for user in Event.regional_coordinators(
                figure.event,
                actor=info.context.user,
            )]
            if figure.event.created_by_id:
                recipients.append(figure.event.created_by_id)

            Notification.send_safe_multiple_notifications(
                recipients=recipients,
                type=_type,
                actor=info.context.user,
                event=figure.event,
                entry=figure.entry,
                figure=figure,
            )

        # Update event status
        Figure.update_event_status_and_send_notifications(figure.event_id)
        figure.event.refresh_from_db()

        return UnapproveFigure(result=figure, errors=None, ok=True)


class ReRequestReviewFigure(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(FigureType)

    @staticmethod
    @permission_checker(['entry.change_figure'])
    @is_authenticated()
    def mutate(root, info, id):
        figure = Figure.objects.filter(id=id).first()
        if not figure:
            return ReRequestReviewFigure(errors=[
                dict(field='nonFieldErrors', messages=gettext('Figure does not exist.'))
            ])

        # NOTE: State machine with states defined in FIGURE_REVIEW_STATUS
        if figure.review_status != Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS:
            return ReRequestReviewFigure(errors=[
                dict(field='nonFieldErrors', messages=gettext('Only in-progress figures can be re-requested review'))
            ])

        figure.review_status = Figure.FIGURE_REVIEW_STATUS.REVIEW_RE_REQUESTED
        figure.approved_by = None
        figure.approved_on = None
        figure.save()

        if figure.event.assignee_id:
            Notification.send_safe_multiple_notifications(
                event=figure.event,
                figure=figure,
                entry=figure.entry,
                recipients=[figure.event.assignee_id],
                actor=info.context.user,
                type=Notification.Type.FIGURE_RE_REQUESTED_REVIEW,
            )

        Figure.update_event_status_and_send_notifications(figure.event_id)
        figure.event.refresh_from_db()

        return ReRequestReviewFigure(result=figure, errors=None, ok=True)


class BulkUpdateFigures(BulkUpdateMutation):
    class Arguments(BulkUpdateMutation.Arguments):
        items = graphene.List(graphene.NonNull(FigureUpdateInputType))

    model = Figure
    serializer_class = FigureSerializer
    result = graphene.List(FigureType)
    deleted_result = graphene.List(graphene.NonNull(FigureType))
    permissions = ['entry.add_figure', 'entry.change_figure', 'entry.delete_figure']

    @staticmethod
    def get_queryset():
        return Figure.objects.all()

    @classmethod
    @transaction.atomic
    def delete_item(cls, figure, context):
        bulk_manager: BulkUpdateFigureManager = context['bulk_manager']
        figure = super().delete_item(figure, context)

        if notification_type := get_figure_notification_type(figure.event, is_deleted=True):
            send_figure_notifications(
                figure,
                context['request'].user,
                notification_type,
                is_deleted=True,
            )
        bulk_manager.add_event(figure.event_id)
        return figure

    @classmethod
    def mutate(cls, *args, **kwargs):
        with BulkUpdateFigureManager() as bulk_manager:
            return super().mutate(*args, **kwargs, context={'bulk_manager': bulk_manager})


class Mutation(object):
    create_entry = CreateEntry.Field()
    update_entry = UpdateEntry.Field()
    delete_entry = DeleteEntry.Field()
    # source preview
    create_source_preview = CreateSourcePreview.Field()
    # figure tags
    create_figure_tag = CreateFigureTag.Field()
    update_figure_tag = UpdateFigureTag.Field()
    delete_figure_tag = DeleteFigureTag.Field()
    # exports
    export_entries = ExportEntries.Field()
    export_figures = ExportFigures.Field()
    export_figure_tags = ExportFigureTags.Field()
    bulk_update_figures = BulkUpdateFigures.Field()
    # figure
    delete_figure = DeleteFigure.Field()
    approve_figure = ApproveFigure.Field()
    unapprove_figure = UnapproveFigure.Field()
    re_request_review_figure = ReRequestReviewFigure.Field()
