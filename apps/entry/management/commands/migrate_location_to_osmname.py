import requests
import csv
import json
import logging
from datetime import datetime, timedelta
import pandas as pd
from functools import reduce
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

            # TODO: skip successful queries on continue

            rows = reduce(
                lambda xs,
                ys: xs + ys,
                [
                    [
                        {
                            **row,
                            "query": location.strip(),
                            # TODO: check if we can split commas, semicolons, etc.
                        } for location in row['locations'].split(',')
                    ] for row in reader
                ]
            )

            total_count = len(rows)
            total_elapsed_for_successful = 0

            def print_stats():
                success_count = len(osmname_response)
                failure_count = len(osmname_response_error_list)
                remaining_count = total_count - success_count - failure_count

                remaining_time = remaining_count * (total_elapsed_for_successful / success_count) \
                    if success_count > 0 else 0

                formatted_remaining_time = str(timedelta(seconds=remaining_time))
                print(
                    f'''
                        Completed: {success_count}\tErrored: {failure_count}\t
                        Total: {total_count}\tETA: {formatted_remaining_time}s
                    '''
                )

            def update_csv_error():
                error_data = pd.DataFrame(osmname_response_error_list)
                error_data.to_csv('location_error.csv', index=False)

            def update_csv_success():
                data = pd.DataFrame(osmname_response)
                data.to_csv('osmname.csv', index=False)

            for row in rows:
                query = row['query']
                iso = row['iso']

                if iso and iso in Figure.SUPPORTED_OSMNAME_COUNTRY_CODES:
                    try:
                        start_time = datetime.now()
                        osm_endpoint = requests.get(f'https://osmnames.idmcdb.org/{iso}/q/{query}.js')
                        end_time = datetime.now()
                    except requests.exceptions.ConnectionError:
                        # TODO: also add a column on osmname_response_error to log what the error was
                        logger.error(f'Couldnot query osmname for {query}')
                        # Store the figure_id and location_name
                        osmname_response_error = dict()
                        osmname_response_error['figure_id'] = row['id']
                        osmname_response_error['location_name'] = query
                        osmname_response_error['error_discription'] = 'connection_error'
                        osmname_response_error_list.append(osmname_response_error)

                        print_stats()
                        update_csv_error()
                        continue
                else:
                    try:
                        start_time = datetime.now()
                        osm_endpoint = requests.get(f'https://osmnames.idmcdb.org/q/{query}.js')
                        end_time = datetime.now()
                    except requests.exceptions.ConnectionError:
                        # TODO: also add a column on osmname_response_error to log what the error was
                        logger.error(f'Couldnot query osmname for {query}')
                        # Store the id and location_name
                        osmname_response_error = dict()
                        osmname_response_error['figure_id'] = row['id']
                        osmname_response_error['location_name'] = query
                        osmname_response_error['error_discription'] = 'connection_error'
                        osmname_response_error_list.append(osmname_response_error)

                        print_stats()
                        update_csv_error()
                        continue
                if osm_endpoint.status_code != 200:
                    # TODO: also add a column on osmname_response_error to log what the error was
                    logger.error(f'Couldnot query osmname for {query}: Status Code: {osm_endpoint.status_code}')
                    # Store the id and location_name
                    osmname_response_error = dict()
                    osmname_response_error['figure_id'] = row['id']
                    osmname_response_error['location_name'] = query
                    osmname_response_error['error_discription'] = f'status_code: {osm_endpoint.status_code}'
                    osmname_response_error_list.append(osmname_response_error)

                    print_stats()
                    update_csv_error()
                    continue
                try:
                    osm_endpoint_response_json = json.loads(osm_endpoint.text)
                except json.decoder.JSONDecodeError:
                    # TODO: also add a column on osmname_response_error to log what the error was
                    logger.error(f'Couldnot query osmname for {query}')
                    # Store the id and location_name
                    osmname_response_error = dict()
                    osmname_response_error['figure_id'] = row['id']
                    osmname_response_error['location_name'] = query
                    osmname_response_error['error_discription'] = 'json_parse_error'
                    osmname_response_error_list.append(osmname_response_error)
                    print_stats()
                    update_csv_error()
                    continue

                if len(osm_endpoint_response_json['results']) > 0:
                    # extract the first response
                    osm_endpoint_response = osm_endpoint_response_json['results'][0]
                    osm_endpoint_response['uuid'] = uuid.uuid4()
                    osm_endpoint_response['figure_id'] = row['id']
                    osm_endpoint_response['query_string'] = query
                    osm_endpoint_response['query_iso'] = iso or None
                    osmname_response.append(osm_endpoint_response)

                    update_csv_success()
                    total_elapsed = (end_time - start_time).seconds
                    total_elapsed_for_successful += total_elapsed
                    print_stats()
                else:
                    # TODO: also add a column on osmname_response_error to log what the error was
                    osmname_response_error = dict()
                    osmname_response_error['figure_id'] = row['id']
                    osmname_response_error['location_name'] = query
                    osmname_response_error['error_discription'] = 'empty_response'
                    osmname_response_error_list.append(osmname_response_error)
                    print_stats()
                    update_csv_error()
