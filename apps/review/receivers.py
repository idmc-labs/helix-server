from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Review, ReviewComment


@receiver(post_save, sender=Review)
@receiver(post_save, sender=ReviewComment)
def update_entry_reviewer_status(sender, instance, created, **kwargs):
    if created:
        from apps.entry.models import EntryReviewer
        entry_reviewer, _ = EntryReviewer.objects.get_or_create(
            entry=instance.entry,
            reviewer=instance.created_by,
        )
        if entry_reviewer.status == EntryReviewer.REVIEW_STATUS.TO_BE_REVIEWED:
            entry_reviewer.status = EntryReviewer.REVIEW_STATUS.UNDER_REVIEW
            entry_reviewer.save()
