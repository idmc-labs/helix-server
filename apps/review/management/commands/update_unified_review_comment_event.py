from django.core.management.base import BaseCommand
from django.db import models

from apps.review.models import UnifiedReviewComment
from apps.entry.models import Figure


class Command(BaseCommand):
    help = "Update Unified review comment events related to figure"

    def handle(self, *args, **options):
        unified_review_comment_qs = UnifiedReviewComment.objects.update(
            event_id=models.Subquery(
                Figure.objects.filter(
                    pk=models.OuterRef('figure_id')
                ).values('event_id')
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Updated UnifiedReviewComment: {unified_review_comment_qs}'
            )
        )
        return super().handle(*args, **options)
