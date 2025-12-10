import random
import typing

from apps.entry.models import Figure
from apps.event.models import Event
from apps.notification.models import Notification
from apps.users.models import User


def generate_idu_from_figure_data(figure_data: typing.Dict) -> str:
    # TODO: Improve IDU generation logic, take appropiriate data from UI
    cause_field = figure_data.get("main_trigger") or "(Main trigger)"
    source_type = figure_data.get("source_type") or "(Source Type)"
    location_field = figure_data.get("location") or "(Location)"
    start_date_field = figure_data.get("start_date") or "(Start Date of Event DD/MM/YYY)"
    unit_field = figure_data.get("unit") or "(People or Household)"
    quantifier_field = figure_data.get("quantifier") or "Quantifier: More than, Around, Less than, At least..."
    displacement_field = figure_data.get("displacement_term") or "(Displacement term: Displaced, ...)"
    figure_field = figure_data.get("figure") or "(Figure)"

    idu = ""
    rand = random.randint(0, 2)
    if rand == 0:
        idu = (
            f"According to {source_type}, {quantifier_field} {figure_field} {unit_field}"
            f"were {displacement_field} in {location_field} due to {cause_field} on {start_date_field}."
        )
    elif rand == 1:
        idu = (
            f"{quantifier_field} {figure_field} {unit_field}"
            f"were {displacement_field} due to {cause_field} on {start_date_field} in {location_field}, "
            f"according to {source_type}."
        )
    else:
        idu = (
            f"{cause_field} resulted in {quantifier_field} {figure_field} {unit_field}"
            f"being {displacement_field} in {location_field} on {start_date_field}, according to {source_type}."
        )
    return idu.capitalize()


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
        user["id"]
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
        **(dict(figure=figure) if not is_deleted else dict()),
    )


class BulkUpdateFigureManager:
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
