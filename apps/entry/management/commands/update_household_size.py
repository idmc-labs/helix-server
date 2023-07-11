import csv
from django.core.management.base import BaseCommand
from apps.entry.models import Figure


class Command(BaseCommand):

    help = "Update household size"

    def add_arguments(self, parser):
        parser.add_argument('household_file')

    def handle(self, *args, **kwargs):
        disaster_csv_file = kwargs['household_file']
        with open(disaster_csv_file, 'r') as disaster_csv_file:
            reader = csv.DictReader(disaster_csv_file)
            for item in reader:
                household_size = item['household_size']
                figure = Figure.objects.get(old_id=item['id'])
                print(
                    f"Household size updated to {household_size} from {figure.household_size} of figure {figure.id}"
                )
                figure.household_size = household_size
                figure.save()
