import csv
import logging
from django.db import models
from django.db.models.functions import Concat
from django.core.management.base import BaseCommand
from datetime import date

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

        figures_to_convert_to_recommended_qs = Figure.objects.filter(
            id___in=ids,
        )
        for figure in figures_to_convert_to_recommended_qs:
            figure.role = Figure.ROLE.RECOMMENDED
            figure.end_date = date(figure.start_date.year, 12, 31)
            figure.save()

        figures_to_convert_to_recommended_qs.update(
            role=Figure.ROLE.RECOMMENDED,
            end_date=Concat(
                'start_date__year',
                models.Value('-12-31'),
                output_field=models.CharField(),
            )
        )

        print(f'Updated {figures_to_convert_to_recommended_qs.count()} stock figures as recommended')
