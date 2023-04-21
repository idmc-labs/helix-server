import csv
import logging
from django.core.management.base import BaseCommand
from apps.country.models import Country
from apps.gidd.models import ConflictLegacy, DisasterLegacy

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Migrate legacy conflict data"

    def add_arguments(self, parser):
        parser.add_argument('conflict_csv_file')
        parser.add_argument('disaster_csv_file')

    def handle(self, *args, **kwargs):
        country_data = Country.objects.values('iso3', 'idmc_short_name')
        country_iso3_map = {item['iso3']: item['idmc_short_name'] for item in country_data}
        conflict_csv_file = kwargs['conflict_csv_file']
        disaster_csv_file = kwargs['disaster_csv_file']

        ConflictLegacy.objects.all().delete()
        DisasterLegacy.objects.all().delete()

        def format_gidd_number(number):
            if number == 0:
                return number
            elif number:
                return number
            else:
                return None

        with open(conflict_csv_file, 'r') as conflict_csv_file:
            reader = csv.DictReader(conflict_csv_file)
            ConflictLegacy.objects.bulk_create(
                [
                    ConflictLegacy(
                        iso3=old_conflict['iso3'],
                        year=old_conflict['year'],
                        country_name=country_iso3_map[old_conflict['iso3']],
                        new_displacement=format_gidd_number(old_conflict['new_displacement']),
                        total_displacement=format_gidd_number(old_conflict['total_displacement']),
                    ) for old_conflict in reader
                ]
            )

        with open(disaster_csv_file, 'r') as disaster_csv_file:
            reader = csv.DictReader(disaster_csv_file)
            DisasterLegacy.objects.bulk_create(
                [
                    DisasterLegacy(
                        iso3=old_disaster['iso3'],
                        year=old_disaster['year'],
                        event_name=old_disaster['event_name'],
                        country_name=country_iso3_map[old_disaster['iso3']],
                        start_date=old_disaster['start_date'] or None,
                        start_date_accuracy=old_disaster['start_date_accuracy'],
                        end_date=old_disaster['end_date'] or None,
                        end_date_accuracy=old_disaster['end_date_accuracy'],
                        hazard_category=old_disaster['hazard_category'],
                        hazard_sub_category=old_disaster['hazard_sub_category'],
                        hazard_type=old_disaster['hazard_type'],
                        hazard_sub_type=old_disaster['hazard_sub_type'],
                        new_displacement=format_gidd_number(old_disaster['new_displacement']),
                    ) for old_disaster in reader
                ]
            )
