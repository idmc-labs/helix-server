import json

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
import requests


class Command(BaseCommand):
    help = 'Split country geojson'

    def handle(self, *args, **options):
        from apps.country.models import Country

        geojson_url = 'https://gist.githubusercontent.com/matemies/71f803153b69a84649a6fe856b033072/raw/c40f3a66733043ca0113ee7c15a3e2c58bb769df/map.geojson'  # noqa E501
        response = requests.get(geojson_url).json()
        countries = response['features']
        print('Starting country geojson dumps...')
        for country in countries:
            default_storage.save(
                Country.geojson_path(country['properties']['iso3']),
                ContentFile(json.dumps(country))
            )
        print('Dumped country geojsons.')
