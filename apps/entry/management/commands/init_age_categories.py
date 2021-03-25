from django.core.management.base import BaseCommand

from apps.entry.constants import DISAGGREGATED_AGE_CATEGORIES
from apps.entry.models import (
    DisaggregatedAgeCategory,
)


class Command(BaseCommand):
    help = 'Initialize or update disaggregated age categories.'

    def handle(self, *args, **options):
        for item in DISAGGREGATED_AGE_CATEGORIES:
            DisaggregatedAgeCategory.objects.get_or_create(name=item)
        self.stdout.write(self.style.SUCCESS(
            'Saved {} disaggregated age categories.'.format(
                DisaggregatedAgeCategory.objects.count(),
            )
        ))
