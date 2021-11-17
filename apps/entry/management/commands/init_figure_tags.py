from django.core.management.base import BaseCommand

from apps.entry.constants import FIGURE_TAGS
from apps.entry.models import (
    FigureTag,
)


class Command(BaseCommand):
    help = 'Initialize or update figure tags and figure terms.'

    def handle(self, *args, **options):
        for tag in FIGURE_TAGS:
            FigureTag.objects.get_or_create(name=tag)
        self.stdout.write(self.style.SUCCESS(
            'Saved {} figure tags.'.format(
                FigureTag.objects.count(),
            )
        ))
