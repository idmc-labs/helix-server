import json
from django.core.management.base import BaseCommand
from apps.helixmigration.models import Facts
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.core import serializers


class NestableKeyTextTransform:
    def __new__(cls, field, *path):
        if not path:
            raise ValueError("Path must contain at least one key.")
        head, *tail = path
        field = KeyTextTransform(head, field)
        for head in tail:
            field = KeyTextTransform(head, field)
        return field


class Command(BaseCommand):
    '''
    This command requires old database connection, which is currently
    in feature/find_bugs branch
    '''

    help = 'Generate moved location dump'

    def get_lat_lon_osm_id_form_locations(self, location):
        return {
            'lat': location['latlng'][0],
            'lng': location['latlng'][1],
            'osm_id': location['geolocation']['osm_id'],
        }

    def handle(self, *args, **options):
        facts = Facts.objects.using('helixmigration').annotate(
            geo_locations=NestableKeyTextTransform(
                "locations", "locations"
            ),
        ).filter(geo_locations__isnull=False)

        # Serializer json
        serialized_facts = serializers.serialize("json", facts, fields=('id', 'locations'))
        moved_locations = []

        # Create dump for moved locations only
        for fact in json.loads(serialized_facts):
            location_dict = {'figure_old_id': fact['pk'], 'locations': []}
            for location_item_to_update in fact['fields']['locations']['locations']:
                if location_item_to_update['moved']:
                    location_dict['locations'].append(
                        self.get_lat_lon_osm_id_form_locations(location_item_to_update)
                    )

            # Only append moved locations
            if location_dict['locations']:
                moved_locations.append(location_dict)

        # Write to json file
        out_file = open("moved_location_dump.json", "w")
        json.dump(
            moved_locations,
            out_file,
            indent=6,
            ensure_ascii=False,
        )
        out_file.close()
