from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    class NotificationType(models.IntegerChoices):
        FIGURE_APPROVED = 0, 'Figure approved'
        FIGURE_RE_REQUESTED_REVIEW = 1, 'Figure re-requested review'
        FIGURE_UN_APPROVED = 2, 'Figure un-approved'
        EVENT_ASSIGNED = 3, 'Event assigned'
        EVENT_ASSIGNEE_CLEARED = 4, 'Event assignee cleared'
        EVENT_SIGNED_OFF = 5, 'Event signed off'

    notification_type = models.IntegerField(
        choices=NotificationType.choices,
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
        return str(self.notification_type)
