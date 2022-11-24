from django.db import models
from django_enumfield import enum
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    class Type(enum.Enum):
        FIGURE_APPROVED = 0
        FIGURE_RE_REQUESTED_REVIEW = 1
        FIGURE_UN_APPROVED = 2
        FIGURE_CREATED = 3
        FIGURE_UPDATED = 4
        FIGURE_DELETED = 5
        FIGURE_UNAPPROVED_IN_SIGNED_EVENT = 6

        EVENT_ASSIGNED = 101
        EVENT_ASSIGNEE_CLEARED = 102
        EVENT_SIGNED_OFF = 103
        EVENT_SELF_ASSIGNED = 104
        EVENT_APPROVED = 105
        EVENT_INCLUDE_TRIANGULATION_CHANGED = 106

        REVIEW_COMMENT_CREATED = 201

        __labels__ = {

            FIGURE_APPROVED: _('Figure approved'),
            FIGURE_RE_REQUESTED_REVIEW: _('Figure re-requested review'),
            FIGURE_UN_APPROVED: _('Figure un-approved'),
            FIGURE_CREATED: _('Figure created'),
            FIGURE_UPDATED: _('Figure updated'),
            FIGURE_DELETED: _('Figure deleted'),
            FIGURE_UNAPPROVED_IN_SIGNED_EVENT: _('Figure unapproved in signed event'),

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
        related_name='recipient',
        verbose_name=_('For user')
    )
    actor = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='actor',
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
        related_name='events',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    figure = models.ForeignKey(
        'entry.Figure',
        verbose_name=_('Figure'),
        related_name='figures',
        on_delete=models.CASCADE,
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
    def send_notification(cls, **kwargs):
        return Notification.objects.create(
            **kwargs
        )
