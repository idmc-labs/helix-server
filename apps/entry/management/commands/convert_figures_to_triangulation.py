import csv
import logging
from django.core.management.base import BaseCommand

from apps.entry.models import Figure

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Update figure roles"

    def add_arguments(self, parser):
        parser.add_argument('figures')

    def handle(self, *args, **kwargs):
        figures_file = kwargs['figures']

        with open(figures_file, 'r') as figures_csv_file:
            reader = csv.DictReader(figures_csv_file)

            ids = [figure['id'] for figure in reader]

        figures_to_convert_to_triangulation_qs = Figure.objects.filter(
            id___in=ids,
        )
        figures_to_convert_to_triangulation_qs.update(role=Figure.ROLE.TRIANGULATION)

        print(f'Updated {figures_to_convert_to_triangulation_qs.count()} figures as triangulation')
