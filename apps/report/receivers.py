from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ReportGeneration


@receiver(post_save, sender=ReportGeneration)
def update_entry_reviewer_status(sender, instance, created, **kwargs):
    if created:
        instance.report.is_signed_off = False
        instance.report.is_signed_off_by = None
        instance.report.save(update_fields=['is_signed_off', 'is_signed_off_by'])
    else:
        if instance.is_signed_off:
            instance.report.is_signed_off = True
            instance.report.is_signed_off_by = instance.is_signed_off_by
            instance.report.save(update_fields=['is_signed_off', 'is_signed_off_by'])
