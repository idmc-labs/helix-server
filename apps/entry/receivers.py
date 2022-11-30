from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import Figure


@receiver(post_save, sender=Figure)
def update_event_status_when_figure_created_or_update(sender, instance, created, **kwargs):
    Figure.update_event_status(instance.event)


@receiver(pre_delete, sender=Figure)
def update_event_status_when_figure_deleted(sender, instance, **kwargs):
    Figure.update_event_status(instance.event)
