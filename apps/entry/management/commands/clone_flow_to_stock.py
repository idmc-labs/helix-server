import csv
import logging
from django.core.management.base import BaseCommand

from apps.entry.models import Figure

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Clone flow figure figures to stock figures"

    def add_arguments(self, parser):
        parser.add_argument('figures')

    def handle(self, *args, **kwargs):
        figures_file = kwargs['figures']

        with open(figures_file, 'r') as figures_csv_file:
            reader = csv.DictReader(figures_csv_file)

            ids = [figure['id'] for figure in reader]

        figures_cloned_list = []
        for figure in Figure.objects.filter(
            id__in=ids
        ):
            figure.id = None
            figure.old_id = None
            year = int(figure.start_date.year)
            end_date = f'{year}-12-31'
            figure.end_date = end_date
            figure.role = Figure.ROLE.RECOMMENDED
            figure.save()

            # Also clone disaggregatedage and osmname relations
            geo_locations_list = []
            for geo_location in figure.geo_locations.all():
                geo_location.id = None
                geo_location_obj = geo_location.save()
                geo_locations_list.append(geo_location_obj)
            figure.geo_locations.set(geo_locations_list)

            disaggregation_age_list = []
            for disaggregation_age in figure.disaggregation_age.all():
                disaggregation_age.id = None
                disaggregation_age = disaggregation_age.save()
                disaggregation_age_list.append(disaggregation_age)
            figure.disaggregation_age.set(disaggregation_age_list)

            figures_cloned_list.append(figure.id)

        # Make a list of new figures that were cloned (clear old_id when cloning or we are going to have a bad time)
        print(
            f'Cloned {len(figures_cloned_list)} figures',
            figures_cloned_list,
        )
