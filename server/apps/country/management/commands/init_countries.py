import csv
import json
import os

from django.core.management.base import BaseCommand
from django.conf import settings

from apps.country.models import Country, GeographicalGroup, CountryRegion


class Command(BaseCommand):
    help = 'Initialize Country'

    def handle(self, *args, **options):
        with open(os.path.join(settings.BASE_DIR, 'fixtures', 'geo_entities.csv')) as csvfile:
            reader = csv.reader(csvfile)
            for row in list(reader)[1:]:
                geo_group = GeographicalGroup.objects.get_or_create(name=row[6])[0]
                region = CountryRegion.objects.get_or_create(name=row[7])[0]
                data = dict(
                    iso3=row[0],
                    country_code=int(row[2]) if row[2] else None,
                    idmc_short_name=row[3],
                    idmc_full_name=row[4],
                    name=row[5],
                    geographical_group=geo_group,
                    region=region,
                    sub_region=row[8],
                    centroid=json.loads(row[9]),
                    boundingbox=json.loads(row[10]),
                    idmc_short_name_es=row[11],
                    idmc_short_name_fr=row[12],
                    idmc_short_name_ar=row[13],
                )
                if Country.objects.filter(iso3__iexact=data['iso3']).exists():
                    self.stdout.write(f'{data["name"]} already exists.')
                    continue
                Country.objects.create(**data)

