import requests
from django.core.management.base import BaseCommand
from apps.entry.models import OSMName


class Command(BaseCommand):
    help = 'Update lat lon of moved locations'

    def handle(self, *args, **options):
        figures_with_moved_locations = requests.get(
            "https://helix-copilot-staging-helix-media.s3.amazonaws.com/media/moved_location_dump.json"
        ).json()
        count = 0
        for figure in figures_with_moved_locations:
            old_id = figure['figure_old_id']
            for moved_location in figure['locations']:
                # Make sure if osm name exist in production database
                osm = OSMName.objects.filter(osm_id=moved_location['osm_id'], figures__old_id=old_id).first()
                if osm:
                    osm.lat = moved_location['lat']
                    osm.lon = moved_location['lng']
                    osm.moved = True
                    osm.save()
                    count += 1
        print(f'{count} Figure locations updated')
