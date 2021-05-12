import json
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
import requests

from turfpy.measurement import bbox
from geojson import MultiPolygon


class Command(BaseCommand):
    help = 'Split country geojson'

    def handle(self, *args, **options):
        from apps.country.models import Country

        geojson_url = 'https://gist.githubusercontent.com/matemies/71f803153b69a84649a6fe856b033072/raw/c40f3a66733043ca0113ee7c15a3e2c58bb769df/map.geojson'  # noqa E501
        response = requests.get(geojson_url).json()
        countries = response['features']
        print('Starting country geojson dumps...')
        for country in countries:
            country_iso3 = country['properties']['iso3']
            crs = response['crs'],
            default_storage.save(
                Country.geojson_path(country_iso3),
                ContentFile(json.dumps({
                    'type': 'FeatureCollection',
                    'crs': crs,
                    'name': country_iso3,
                    'features': [country],
                }))
            )

            instance = Country.objects.get(iso3=country['properties']['iso3'])
            multipolygon = MultiPolygon(country['geometry']['coordinates'])
            if multipolygon and instance:
                bb = bbox(multipolygon)
                instance.bounding_box = bb
                instance.save()
        print('Dumped country geojsons.')
