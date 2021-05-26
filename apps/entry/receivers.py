from django.db.models.signals import (
    post_save,
    post_delete,
    m2m_changed,
)
from django.dispatch import receiver

from .models import EntryReviewer, Entry


def update_entry_review_status(entry):
    from apps.entry.models import EntryReviewer
    latest_status = EntryReviewer.objects.filter(
        entry=entry,
    ).order_by('-status').values_list('status', flat=True)
    entry.review_status = None
    if latest_status:
        entry.review_status = latest_status[0]
    entry.save()


@receiver(post_save, sender=EntryReviewer)
@receiver(post_delete, sender=EntryReviewer)
def update_entry_review_status_post_save(sender, instance, **kwargs):
    update_entry_review_status(instance.entry)


@receiver(m2m_changed, sender=Entry.reviewers.through)
def update_entry_review_status_m2m(sender, instance, **kwargs):
    if kwargs['action'] in ['post_add', 'post_remove', 'post_clear']:
        update_entry_review_status(instance)
