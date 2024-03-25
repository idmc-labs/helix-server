from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.entry.models import Figure


class Command(BaseCommand):
    help = 'Populate a calculation_logic field on the Figure table if it was blank for existing data'

    def handle(self, *args, **options):
        figures_without_calculation_logic_data = Figure.objects.filter(
            Q(calculation_logic__isnull=True) | Q(calculation_logic='')
        )

        resp = figures_without_calculation_logic_data.update(calculation_logic='Not available')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully populated the blank calculation_logic field on the Figure table. {resp}')
        )
