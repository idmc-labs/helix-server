import csv
import logging
import datetime
from django.core.management.base import BaseCommand
from apps.country.models import Country
from apps.crisis.models import Crisis
from apps.gidd.models import IdpsSaddEstimate


logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Update idps sadd estimates"

    def add_arguments(self, parser):
        parser.add_argument('csv_file')

    def handle(self, *args, **kwargs):
        def _format_cause(cause_string):
            if cause_string == Crisis.CRISIS_TYPE.CONFLICT.label:
                return Crisis.CRISIS_TYPE.CONFLICT.value
            elif cause_string == Crisis.CRISIS_TYPE.DISASTER.label:
                return Crisis.CRISIS_TYPE.DISASTER.value

        def format_number(number):
            return number.replace(',', '').replace('-', '').strip() or None

        csv_file = kwargs['csv_file']

        iso3_to_country_id_map = {
            item['iso3']: item['id'] for item in Country.objects.values('iso3', 'id')
        }
        iso3_to_country_name_map = {
            item['iso3']: item['idmc_short_name'] for item in Country.objects.values('iso3', 'idmc_short_name')
        }

        with open(csv_file, 'r') as csv_file:
            reader = csv.DictReader(csv_file)
            objects_to_create = []
            for obj in reader:
                # Remove keys spaces
                item = {k.strip(): v for (k, v) in obj.items()}
                objects_to_create.append(
                    IdpsSaddEstimate(
                        iso3=item['ISO3'],
                        country_name=iso3_to_country_name_map.get(item['ISO3']),
                        country_id=iso3_to_country_id_map.get(item['ISO3']),
                        year=datetime.datetime.strptime(item['Year'], "%d/%m/%Y").date().year,
                        sex=item['Sex'],
                        cause=_format_cause(item['Cause']),
                        zero_to_one=format_number(item['0-1']),
                        zero_to_four=format_number(item['0-4']),
                        zero_to_forteen=format_number(item['0-14']),
                        zero_to_sventeen=format_number(item['0-17']),
                        zero_to_twenty_four=format_number(item['0-24']),
                        five_to_elaven=format_number(item['5-11']),
                        five_to_fourteen=format_number(item['5-14']),
                        twelve_to_fourteen=format_number(item['12-14']),
                        twelve_to_sixteen=format_number(item['12-16']),
                        fifteen_to_seventeen=format_number(item['15-17']),
                        fifteen_to_twentyfour=format_number(item['15-24']),
                        twenty_five_to_sixty_four=format_number(item['25-64']),
                        sixty_five_plus=format_number(item['65+']),
                    )
                )
            IdpsSaddEstimate.objects.bulk_create(objects_to_create)
