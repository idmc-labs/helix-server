from django.utils.translation import gettext
import graphene
from graphene_django.filter.utils import get_filtering_args_from_filterset
from django.utils import timezone

from apps.contrib.models import SourcePreview
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
    NestedFigureUpdateSerializer,
)
from apps.extraction.filters import FigureExtractionFilterSet, EntryExtractionFilterSet
from apps.contrib.serializers import SourcePreviewSerializer, ExcelDownloadSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker, is_authenticated
from utils.mutation import generate_input_type_for_serializer
from utils.common import convert_date_object_to_string_in_dict
from apps.notification.models import Notification

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
    serializer_class=NestedFigureUpdateSerializer,
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
        try:
            instance = Entry.objects.get(id=id)
        except Entry.DoesNotExist:
            return DeleteEntry(errors=[
                dict(field='nonFieldErrors', messages=gettext('Entry does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteEntry(result=instance, errors=None, ok=True)


class updateFigure(graphene.Mutation):

    class Arguments:
        data = FigureUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(EntryType)

    @staticmethod
    @permission_checker(['entry.change_figure'])
    def mutate(root, info, data):
        try:
            instance = Figure.objects.get(id=data['id'])
        except Entry.DoesNotExist:
            return updateFigure(errors=[
                dict(field='nonFieldErrors', messages=gettext('Figure does not exist.'))
            ])
        serializer = NestedFigureUpdateSerializer(
            instance=instance, data=data,
            context={'request': info.context.request}, partial=True
        )
        if errors := mutation_is_not_valid(serializer):
            return updateFigure(errors=errors, ok=False)
        instance = serializer.save()
        return updateFigure(result=instance, errors=None, ok=True)


class DeleteFigure(graphene.Mutation):
    from apps.event.models import Event

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
        if instance.event.review_status == Event.EVENT_REVIEW_STATUS.APPROVED:
            Notification.send_multiple_notifications(
                recipients=instance.event.regional_coordinators(
                    event=instance.event
                ),
                actor=info.context.user,
                type=Notification.Type.FIGURE_DELETED_IN_APPROVED_EVENT,
                event=instance.event,
                # TODO: Add proper descriptive text
                text=f'''
                Figure having id {instance.id}, start_date
                {instance.start_date}, end_date {instance.end_date}
                was deleted.
                '''
            )
        if instance.event.review_status == Event.EVENT_REVIEW_STATUS.SIGNED_OFF:
            Notification.send_multiple_notifications(
                recipients=instance.event.regional_coordinators(
                    event=instance.event
                ),
                actor=info.context.user,
                type=Notification.Type.FIGURE_DELETED_IN_SIGNED_EVENT,
                event=instance.event,
            )
        instance.delete()
        return DeleteFigure(errors=None, ok=True)

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


class ExportEntries(graphene.Mutation):
    class Meta:
        arguments = get_filtering_args_from_filterset(
            EntryExtractionFilterSet,
            EntryType
        )

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, **kwargs):
        from apps.contrib.models import ExcelDownload

        serializer = ExcelDownloadSerializer(
            data=dict(
                download_type=int(ExcelDownload.DOWNLOAD_TYPES.ENTRY),
                filters=convert_date_object_to_string_in_dict(kwargs),
            ),
            context=dict(request=info.context.request)
        )
        if errors := mutation_is_not_valid(serializer):
            return ExportEntries(errors=errors, ok=False)
        serializer.save()
        return ExportEntries(errors=None, ok=True)


class ExportFigures(graphene.Mutation):
    class Meta:
        arguments = get_filtering_args_from_filterset(
            FigureExtractionFilterSet,
            FigureType
        )

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, **kwargs):
        from apps.contrib.models import ExcelDownload

        serializer = ExcelDownloadSerializer(
            data=dict(
                download_type=int(ExcelDownload.DOWNLOAD_TYPES.FIGURE),
                filters=convert_date_object_to_string_in_dict(kwargs),
            ),
            context=dict(request=info.context.request)
        )
        if errors := mutation_is_not_valid(serializer):
            return ExportFigures(errors=errors, ok=False)
        serializer.save()
        return ExportFigures(errors=None, ok=True)


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
                dict(field='id', messages=gettext('Figure does not exist.'))
            ])
        figure.review_status = Figure.FIGURE_REVIEW_STATUS.APPROVED.value
        figure.approved_by = info.context.user
        figure.approved_on = timezone.now()
        figure.save()
        # NOTE: To refresh event
        figure.refresh_from_db()
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
                dict(field='id', messages=gettext('Figure does not exist.'))
            ])
        figure.review_status = Figure.FIGURE_REVIEW_STATUS.REVIEW_NOT_STARTED
        if figure.figure_review_comments.all().count() > 0:
            figure.review_status = Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS
        figure.approved_by = None
        figure.approved_on = None
        figure.save()
        if figure.event and figure.event.review_status == Event.EVENT_REVIEW_STATUS.APPROVED:
            Notification.send_multiple_notifications(
                recipients=figure.event.regional_coordinators(
                    event=figure.event,
                    figure=figure,
                ),
                type=Notification.Type.FIGURE_UNAPPROVED_IN_APPROVED_EVENT,
                actor=info.context.user,
                event=figure.event,
                figure=figure,
            )
        if figure.event and figure.event.review_status == Event.EVENT_REVIEW_STATUS.SIGNED_OFF:
            Notification.send_multiple_notifications(
                recipients=figure.event.regional_coordinators(
                    event=figure.event,
                    figure=figure,
                ),
                type=Notification.Type.FIGURE_UNAPPROVED_IN_SIGNED_EVENT,
                actor=info.context.user,
                event=figure.event,
                figure=figure,
            )
        # NOTE: To refresh event
        figure.refresh_from_db()
        return UnapproveFigure(result=figure, errors=None, ok=True)


class ReRequestReivewFigure(graphene.Mutation):
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
            return ReRequestReivewFigure(errors=[
                dict(field='id', messages=gettext('Figure does not exist.'))
            ])
        figure.review_status = Figure.FIGURE_REVIEW_STATUS.REVIEW_RE_REQUESTED
        figure.approved_by = None
        figure.approved_on = None
        figure.save()

        # NOTE: To refresh event
        figure.refresh_from_db()

        if figure.event and figure.event.assignee:
            Notification.send_notification(
                event=figure.event,
                recipient=figure.event.assignee,
                actor=info.context.user,
                type=Notification.Type.FIGURE_RE_REQUESTED_REVIEW,
            )
        return ReRequestReivewFigure(result=figure, errors=None, ok=True)


class Mutation(object):
    create_entry = CreateEntry.Field()
    update_entry = UpdateEntry.Field()
    delete_entry = DeleteEntry.Field()
    create_source_preview = CreateSourcePreview.Field()
    # figure tags
    create_figure_tag = CreateFigureTag.Field()
    update_figure_tag = UpdateFigureTag.Field()
    delete_figure_tag = DeleteFigureTag.Field()
    # exports
    export_entries = ExportEntries.Field()
    export_figures = ExportFigures.Field()
    # figure
    update_figure = updateFigure.Field()
    delete_figure = DeleteFigure.Field()
    # figure reviews
    approve_figure = ApproveFigure.Field()
    unapprove_figure = UnapproveFigure.Field()
    re_request_review_figure = ReRequestReivewFigure.Field()
