from apps.entry.models import Figure
from apps.event.models import Event
from apps.notification.models import Notification
from apps.users.models import User


def get_figure_notification_type(event, is_deleted=False, is_new=False):
    if event.review_status in [
        Event.EVENT_REVIEW_STATUS.SIGNED_OFF,
        Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED,
    ]:
        if is_deleted:
            return Notification.Type.FIGURE_DELETED_IN_SIGNED_EVENT
        if is_new:
            return Notification.Type.FIGURE_CREATED_IN_SIGNED_EVENT
        # For update
        return Notification.Type.FIGURE_UPDATED_IN_SIGNED_EVENT

    elif event.review_status in [
        Event.EVENT_REVIEW_STATUS.APPROVED,
        Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED,
    ]:
        if is_deleted:
            return Notification.Type.FIGURE_DELETED_IN_APPROVED_EVENT
        if is_new:
            return Notification.Type.FIGURE_CREATED_IN_APPROVED_EVENT
        # For update
        return Notification.Type.FIGURE_UPDATED_IN_APPROVED_EVENT


def send_figure_notifications(
    figure: Figure,
    actor: User,
    notification_type: Notification.Type,
    is_deleted: bool = False,
):
    recipients = [
        user['id']
        for user in Event.regional_coordinators(
            figure.event,
            actor=actor,
        )
    ]
    if figure.event.created_by_id:
        recipients.append(figure.event.created_by_id)
    if figure.event.assignee_id:
        recipients.append(figure.event.assignee_id)

    Notification.send_safe_multiple_notifications(
        recipients=recipients,
        actor=actor,
        event=figure.event,
        entry=figure.entry,
        type=notification_type,
        **(
            dict(figure=figure)
            if not is_deleted else dict()
        ),
    )


class BulkUpdateFigureManager():
    def __enter__(self):
        self.event_ids = set()
        return self

    def add_event(self, event_id: int):
        self.event_ids.add(event_id)

    # Note: Using *_ will make typing make this as non context manager
    def __exit__(self, exc_type, exc_value, exc_traceback):
        for event_id in self.event_ids:
            Figure.update_event_status_and_send_notifications(event_id)
