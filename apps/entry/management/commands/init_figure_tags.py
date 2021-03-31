from django.core.management.base import BaseCommand

from apps.entry.constants import FIGURE_TAGS, FIGURE_TERMS
from apps.entry.models import (
    FigureTag,
    FigureTerm,
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
        for identifier, item in FIGURE_TERMS.items():
            ft, _ = FigureTerm.objects.get_or_create(identifier=identifier, name=item['name'])
            ft.is_housing_related = item['housing']
            ft.save()
        self.stdout.write(self.style.SUCCESS(
            'Saved {} figure terms.'.format(
                FigureTerm.objects.count(),
            )
        ))
