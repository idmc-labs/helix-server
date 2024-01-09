from django.core.management.base import BaseCommand
from django.db import transaction

from apps.country.models import HouseholdSize


class Command(BaseCommand):
    help = 'Clone HouseholdSize from one year to another'

    def add_arguments(self, parser):
        parser.add_argument('source_year', type=int)
        parser.add_argument('destination_year', type=int)

    @transaction.atomic
    def handle(self, *_, **options):
        source_year = options['source_year']
        destination_year = options['destination_year']

        existing_count = HouseholdSize.objects.filter(year=destination_year).count()
        if existing_count > 0:
            self.stdout.write(
                self.style.ERROR(
                    f'Destination year already has data: Total records: {existing_count}'
                )
            )
            return

        cloned_data = []
        for row in HouseholdSize.objects.filter(year=source_year).all():
            row.pk = None  # Create new
            row.year = destination_year  # Change year
            cloned_data.append(row)
        resp = HouseholdSize.objects.bulk_create(cloned_data)
        self.stdout.write(
            self.style.SUCCESS(
                f'Success: Total records created: {len(resp)}'
            )
        )
        self.stdout.write('New records:')
        for i in resp:
            self.stdout.write(f'- {i}')
