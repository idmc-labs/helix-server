import typing

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


def get_event_notification_type(event, is_figure_deleted=False, is_figure_new=False):
    return get_figure_notification_type(event, is_deleted=is_figure_deleted, is_new=is_figure_new)


def send_figure_notifications(
    figure: Figure,
    actor: User,
    notification_type: Notification.Type,
    is_deleted: bool = False,
    event: typing.Optional[Event] = None,
):
    _event = event or figure.event

    recipients = [
        user['id']
        for user in Event.regional_coordinators(
            _event,
            actor=actor,
        )
    ]
    if _event.created_by_id:
        recipients.append(_event.created_by_id)
    if _event.assignee_id:
        recipients.append(_event.assignee_id)

    Notification.send_safe_multiple_notifications(
        recipients=recipients,
        actor=actor,
        event=_event,
        entry=figure.entry,
        type=notification_type,
        **(
            dict(figure=figure)
            if not is_deleted else dict()
        ),
    )


class BulkUpdateFigureManager():
    event_ids: typing.Set[int]
    figure_moved_from_event: typing.Set[Event]
    figure_moved_to_event: typing.Set[Event]

    def __enter__(self):
        self.event_ids = set()
        self.figure_moved_from_event = set()
        self.figure_moved_to_event = set()
        return self

    def add_event(self, event_id: int):
        self.event_ids.add(event_id)

    # Note: Using *_ will make typing make this as non context manager
    def __exit__(self, exc_type, exc_value, exc_traceback):
        # Update status
        for event_id in self.event_ids:
            Figure.update_event_status_and_send_notifications(event_id)
