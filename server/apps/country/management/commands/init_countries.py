import csv
import json
import os

from django.core.management.base import BaseCommand
from django.conf import settings
import requests

from apps.country.models import Country, GeographicalGroup, CountryRegion


class Command(BaseCommand):
    help = 'Initialize Country'

    def handle(self, *args, **options):
        bbox_url = 'https://gist.githubusercontent.com/botzill/fc2a1581873200739f6dc5c1daf85a7d/raw/' \
                   '002372a57a40f299a463122c039faf9f927b13fe/countries_bbox.json'
        content = requests.get(bbox_url).json()
        with open(os.path.join(settings.BASE_DIR, 'fixtures', 'geo_entities.csv')) as csvfile:
            reader = csv.reader(csvfile)
            for row in list(reader)[1:]:
                geo_group = GeographicalGroup.objects.get_or_create(name=row[6])[0]
                region = CountryRegion.objects.get_or_create(name=row[7])[0]
                iso3 = row[0]
                bbox = None
                if content.get(iso3):
                    bbox = [
                        content.get(iso3)['sw']['lon'],
                        content.get(iso3)['sw']['lat'],
                        content.get(iso3)['ne']['lon'],
                        content.get(iso3)['ne']['lat'],
                    ]
                data = dict(
                    country_code=int(row[2]) if row[2] else None,
                    idmc_short_name=row[3],
                    idmc_full_name=row[4],
                    name=row[5],
                    geographical_group=geo_group,
                    region=region,
                    sub_region=row[8],
                    centroid=json.loads(row[9]),
                    boundingbox=bbox,
                    idmc_short_name_es=row[11],
                    idmc_short_name_fr=row[12],
                    idmc_short_name_ar=row[13],
                )
                Country.objects.update_or_create(iso3=iso3,
                                                 defaults=data)
        print(f'Loaded {Country.objects.count()} countries.')
