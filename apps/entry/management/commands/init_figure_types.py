from django.core.management.base import BaseCommand

from apps.entry.constants import FIGURE_TYPE_SUB_TYPES
from apps.entry.models import (
    FigureCategory,
)


class Command(BaseCommand):
    help = 'Initialize or update figure types.'

    def handle(self, *args, **options):
        for cat, sub_cats in FIGURE_TYPE_SUB_TYPES.items():
            figure_type = cat
            for sub_cat in sub_cats:
                FigureCategory.objects.get_or_create(name=sub_cat, type=figure_type)
        self.stdout.write(self.style.SUCCESS(
            'Saved {} figure categories.'.format(
                FigureCategory.objects.count(),
            )
        ))
        FigureCategory.objects.filter(name='IDP').delete()
