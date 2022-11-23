from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    class Type(models.IntegerChoices):
        FIGURE_APPROVED = 0, 'Figure approved'
        FIGURE_RE_REQUESTED_REVIEW = 1, 'Figure re-requested review'
        FIGURE_UN_APPROVED = 2, 'Figure un-approved'
        FIGURE_CREATED = 3, 'Figure created'
        FIGURE_UPDATED = 4, 'Figure updated'
        FIGURE_DELETED = 5, 'Figure deleted'
        FIGURE_UNAPPROVED_IN_SIGNED_EVENT = 6, 'Figure unapproved in signed event',

        EVENT_ASSIGNED = 101, 'Event assigned'
        EVENT_ASSIGNEE_CLEARED = 102, 'Event assignee cleared'
        EVENT_SIGNED_OFF = 103, 'Event signed off'
        EVENT_SELF_ASSIGNED = 104, 'Event self assigned'
        EVENT_APPROVED = 105, 'Event approved'
        EVENT_INCLUDE_TRIANGULATION_CHANGED = 106, 'Event include triangulation changed'

        REVIEW_COMMENT_CREATED = 201, 'Comment created'

    type = models.IntegerField(
        choices=Type.choices,
        verbose_name=_("Notification Type")
    )
    recipient = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        verbose_name=_('For user')
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
