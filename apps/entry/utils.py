from django.db import transaction
from apps.entry.models import Figure
from apps.event.models import Event
from apps.notification.models import Notification
from apps.entry.serializers import FigureSerializer


def bulk_create_update_delete_figures(validated_data, delete_ids, context):
    with transaction.atomic():

        created_figures_for_signed_off_events = []
        created_figures_for_approved_events = []

        updated_figures_for_signed_off_events = []
        updated_figures_for_approved_events = []
        updated_figures_for_other_events = []

        # delete missing figures
        figures_to_delete = Figure.objects.filter(
            id__in=delete_ids
        )
        deleted_figures_for_signed_off_events = list(
            figures_to_delete.filter(
                event__review_status=Event.EVENT_REVIEW_STATUS.SIGNED_OFF
            )
        )
        deleted_figures_for_approved_events = list(
            figures_to_delete.filter(
                event__review_status=Event.EVENT_REVIEW_STATUS.APPROVED
            )
        )
        affected_events = Event.objects.filter(
            id__in=figures_to_delete.values('event__id')
        ).distinct('id')
        affected_event_ids = list(affected_events.values_list('id', flat=True))

        # delete missing figures
        figures_to_delete.delete()

        objects_created_or_updated = []

        for each in validated_data:
            is_new_figure = not each.get('id')
            # create new figures
            if not each.get('id'):
                fig_ser = FigureSerializer(context=context)
            # update existing figures
            else:
                fig_ser = FigureSerializer(
                    instance=Figure.objects.get(id=each['id']),
                    partial=True,
                    context=context,
                )

            fig_ser._validated_data = {**each}
            fig_ser._errors = {}
            figure = fig_ser.save()
            objects_created_or_updated.append(figure)
            if is_new_figure and figure.event.review_status == Event.EVENT_REVIEW_STATUS.SIGNED_OFF:
                created_figures_for_signed_off_events.append(figure)
            elif is_new_figure and figure.event.review_status == Event.EVENT_REVIEW_STATUS.APPROVED:
                created_figures_for_approved_events.append(figure)
            elif not is_new_figure and figure.event.review_status == Event.EVENT_REVIEW_STATUS.SIGNED_OFF:
                updated_figures_for_signed_off_events.append(figure)
            elif not is_new_figure and figure.event.review_status == Event.EVENT_REVIEW_STATUS.APPROVED:
                updated_figures_for_approved_events.append(figure)
            elif not is_new_figure:
                updated_figures_for_other_events.append(figure)

            affected_event_ids.append(figure.event_id)

        for figure in deleted_figures_for_signed_off_events:
            recipients = [user['id'] for user in Event.regional_coordinators(
                figure.event,
                actor=context['request'].user,
            )]
            if figure.event.created_by_id:
                recipients.append(figure.event.created_by_id)
            if figure.event.assignee_id:
                recipients.append(figure.event.assignee_id)
            Notification.send_safe_multiple_notifications(
                recipients=recipients,
                actor=context['request'].user,
                type=Notification.Type.FIGURE_DELETED_IN_SIGNED_EVENT,
                event=figure.event,
                entry=figure.entry,
            )
        for figure in deleted_figures_for_approved_events:
            recipients = [user['id'] for user in Event.regional_coordinators(
                figure.event,
                actor=context['request'].user,
            )]
            if figure.event.created_by_id:
                recipients.append(figure.event.created_by_id)
            if figure.event.assignee_id:
                recipients.append(figure.event.assignee_id)
            Notification.send_safe_multiple_notifications(
                recipients=recipients,
                actor=context['request'].user,
                type=Notification.Type.FIGURE_DELETED_IN_APPROVED_EVENT,
                event=figure.event,
                entry=figure.entry,
            )
        for figure in updated_figures_for_signed_off_events:
            recipients = [user['id'] for user in Event.regional_coordinators(
                figure.event,
                actor=context['request'].user,
            )]
            if figure.event.created_by_id:
                recipients.append(figure.event.created_by_id)
            if figure.event.assignee_id:
                recipients.append(figure.event.assignee_id)
            Notification.send_safe_multiple_notifications(
                recipients=recipients,
                actor=context['request'].user,
                type=Notification.Type.FIGURE_UPDATED_IN_SIGNED_EVENT,
                event=figure.event,
                entry=figure.entry,
                figure=figure,
            )
            Figure.update_figure_status(figure)
        for figure in updated_figures_for_approved_events:
            recipients = [user['id'] for user in Event.regional_coordinators(
                figure.event,
                actor=context['request'].user,
            )]
            if figure.event.created_by_id:
                recipients.append(figure.event.created_by_id)
            if figure.event.assignee_id:
                recipients.append(figure.event.assignee_id)
            Notification.send_safe_multiple_notifications(
                recipients=recipients,
                actor=context['request'].user,
                type=Notification.Type.FIGURE_UPDATED_IN_APPROVED_EVENT,
                event=figure.event,
                entry=figure.entry,
                figure=figure,
            )
            Figure.update_figure_status(figure)
        for figure in updated_figures_for_other_events:
            Figure.update_figure_status(figure)
        for figure in created_figures_for_signed_off_events:
            recipients = [user['id'] for user in Event.regional_coordinators(
                figure.event,
                actor=context['request'].user,
            )]
            if figure.event.created_by_id:
                recipients.append(figure.event.created_by_id)
            if figure.event.assignee_id:
                recipients.append(figure.event.assignee_id)
            Notification.send_safe_multiple_notifications(
                recipients=recipients,
                actor=context['request'].user,
                type=Notification.Type.FIGURE_CREATED_IN_SIGNED_EVENT,
                event=figure.event,
                entry=figure.entry,
                figure=figure,
            )
        for figure in created_figures_for_approved_events:
            recipients = [user['id'] for user in Event.regional_coordinators(
                figure.event,
                actor=context['request'].user,
            )]
            if figure.event.created_by_id:
                recipients.append(figure.event.created_by_id)
            if figure.event.assignee_id:
                recipients.append(figure.event.assignee_id)
            Notification.send_safe_multiple_notifications(
                recipients=recipients,
                actor=context['request'].user,
                type=Notification.Type.FIGURE_CREATED_IN_APPROVED_EVENT,
                event=figure.event,
                entry=figure.entry,
                figure=figure,
            )
        for event_id in affected_event_ids:
            Figure.update_event_status_and_send_notifications(event_id)
        return objects_created_or_updated
