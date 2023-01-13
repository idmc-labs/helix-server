from django.db import models
from django_enumfield import enum
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    class Type(enum.Enum):
        FIGURE_RE_REQUESTED_REVIEW = 0
        FIGURE_CREATED_IN_APPROVED_EVENT = 1
        FIGURE_UPDATED_IN_APPROVED_EVENT = 2
        FIGURE_DELETED_IN_APPROVED_EVENT = 3
        FIGURE_CREATED_IN_SIGNED_EVENT = 4
        FIGURE_UPDATED_IN_SIGNED_EVENT = 5
        FIGURE_DELETED_IN_SIGNED_EVENT = 6
        FIGURE_UNAPPROVED_IN_SIGNED_EVENT = 7
        FIGURE_UNAPPROVED_IN_APPROVED_EVENT = 8

        EVENT_ASSIGNED = 101
        EVENT_ASSIGNEE_CLEARED = 102
        EVENT_SIGNED_OFF = 103
        EVENT_SELF_ASSIGNED = 104
        EVENT_APPROVED = 105
        EVENT_INCLUDE_TRIANGULATION_CHANGED = 106

        REVIEW_COMMENT_CREATED = 201

        __labels__ = {

            FIGURE_RE_REQUESTED_REVIEW: _('Figure re-requested review'),
            FIGURE_CREATED_IN_APPROVED_EVENT: _('Figure created in approved event'),
            FIGURE_UPDATED_IN_APPROVED_EVENT: _('Figure updated in approved event'),
            FIGURE_DELETED_IN_APPROVED_EVENT: _('Figure deleted in approved event'),
            FIGURE_CREATED_IN_SIGNED_EVENT: _('Figure created in signed-off event'),
            FIGURE_UPDATED_IN_SIGNED_EVENT: _('Figure updated in signed-off event'),
            FIGURE_DELETED_IN_SIGNED_EVENT: _('Figure deleted in signed-off event'),
            FIGURE_UNAPPROVED_IN_SIGNED_EVENT: _('Figure unapproved in signed-off event'),
            FIGURE_UNAPPROVED_IN_APPROVED_EVENT: _('Figure unapproved in approved event'),

            EVENT_ASSIGNED: _('Event assigned'),
            EVENT_ASSIGNEE_CLEARED: _('Event assignee cleared'),
            EVENT_SIGNED_OFF: _('Event signed off'),
            EVENT_SELF_ASSIGNED: _('Event self assigned'),
            EVENT_APPROVED: _('Event approved'),
            EVENT_INCLUDE_TRIANGULATION_CHANGED: _('Event include triangulation changed'),

            REVIEW_COMMENT_CREATED: _('Comment created'),
        }

    type = enum.EnumField(
        enum=Type,
        verbose_name=_("Notification Type")
    )

    recipient = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='recipient_notifications',
        verbose_name=_('For user')
    )
    actor = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='actor_notifications',
        verbose_name=_('Actor'),
        null=True,
        blank=True,
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name=_('Is read?'),
        help_text=_('Whether notification has been marked as read')
    )
    event = models.ForeignKey(
        'event.Event',
        verbose_name=_('Event'),
        related_name='notifications',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    figure = models.ForeignKey(
        'entry.Figure',
        verbose_name=_('Figure'),
        related_name='notifications',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    entry = models.ForeignKey(
        'entry.Entry',
        verbose_name=_('Entry'),
        related_name='notifications',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    review_comment = models.ForeignKey(
        'review.UnifiedReviewComment',
        verbose_name=_('Unified review comment'),
        related_name='notifications',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    text = models.CharField(
        verbose_name=_('Raw text'),
        max_length=256,
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at'),
        help_text=_('When notification was created')
    )

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")

    def __str__(self):
        return str(self.type)

    @classmethod
    def send_safe_multiple_notifications(
        cls,
        recipients,
        actor,
        type,
        figure=None,
        event=None,
        entry=None,
        text=None,
        review_comment=None,
    ):
        recipient_set = set(recipients)
        # FIXME: do we need to just pass actor_id?
        if actor and actor.id in recipient_set:
            # TODO: log to sentry if recipient ids contact actor id
            # It indicates we have a problem with some logic
            recipient_set.remove(actor.id)

        recipient_list = list(recipient_set)

        Notification.objects.bulk_create(
            [
                Notification(
                    recipient_id=recipient_id,
                    type=type,
                    actor=actor,
                    figure=figure,
                    event=event,
                    entry=entry,
                    text=text,
                    review_comment=review_comment,
                ) for recipient_id in recipient_list
            ]
        )
