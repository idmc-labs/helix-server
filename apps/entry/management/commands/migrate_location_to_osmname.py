import requests
import csv
import json
import logging
import pandas as pd
import uuid

from django.core.management.base import BaseCommand

from apps.entry.models import Figure


logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Migrate location to osmname"

    def add_arguments(self, parser):
        parser.add_argument('input_file')

    def handle(self, *args, **kwargs):
        csv.field_size_limit(100000000)
        input_file = kwargs['input_file']
        with open(input_file, 'r') as input_file:
            reader = csv.DictReader(input_file)
            osmname_response_error_list = []
            osmname_response = []
            count = 0
            error_count = 0
            for row in reader:
                location_name = row['locations']
                iso = row['iso']
                for name in location_name.split(','):
                    name = name.strip()
                    if iso and iso in Figure.SUPPORTED_OSMNAME_COUNTRY_CODES:
                        try:
                            osm_endpoint = requests.get(f'https://osmnames.idmcdb.org/{iso}/q/{name}.js')
                        except requests.exceptions.ConnectionError:
                            continue
                    else:
                        try:
                            osm_endpoint = requests.get(f'https://osmnames.idmcdb.org/q/{name}.js')
                        except requests.exceptions.ConnectionError:
                            continue
                    if osm_endpoint.status_code != 200:
                        logger.error(f'Couldnot query osmname for {name}')
                        # Store the id and location_name
                        osmname_response_error = dict()
                        osmname_response_error['id'] = row['id']
                        osmname_response_error['location_name'] = name
                        osmname_response_error_list.append(osmname_response_error)
                    try:
                        osm_endpoint_response_json = json.loads(osm_endpoint.text)
                    except json.decoder.JSONDecodeError:
                        continue
                    if len(osm_endpoint_response_json['results']) > 0:
                        # extract the first response
                        osm_endpoint_response = osm_endpoint_response_json['results'][0]
                        osm_endpoint_response['uuid'] = uuid.uuid4()
                        osm_endpoint_response['id'] = row['id']
                        osm_endpoint_response['query_string'] = name
                        osm_endpoint_response['query_iso'] = iso or None
                        count += 1
                        osmname_response.append(osm_endpoint_response)
                    else:
                        osmname_response_error = dict()
                        osmname_response_error['id'] = row['id']
                        osmname_response_error['location_name'] = name
                        error_count += 1
                        osmname_response_error_list.append(osmname_response_error)
                    error_data = pd.DataFrame(osmname_response_error_list)
                    error_data.to_csv('location_error.csv', index=False)
                    data = pd.DataFrame(osmname_response)
                    data.to_csv('osmname.csv', index=False)
                print(f'{count} Locations extracted')
                print(f'{error_count} Locations extraction error')