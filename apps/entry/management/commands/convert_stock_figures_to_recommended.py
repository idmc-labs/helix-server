import csv
import logging
from django.db import models, transaction
from django.db.models.functions import Concat, Cast
from django.core.management.base import BaseCommand
from datetime import date

from apps.entry.models import Figure

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Update stock figure roles as recommended"

    def add_arguments(self, parser):
        parser.add_argument('figures')

    @transaction.atomic
    def handle(self, *args, **kwargs):
        figures_file = kwargs['figures']

        with open(figures_file, 'r') as figures_csv_file:
            reader = csv.DictReader(figures_csv_file)

            ids = [figure['id'] for figure in reader]

        figures_to_convert_to_recommended_qs = Figure.objects.filter(
            id__in=ids,
        )

        figures_to_convert_to_recommended_qs.update(
            role=Figure.ROLE.RECOMMENDED,
            end_date=Cast(Concat(
                'start_date__year',
                models.Value('-12-31'),
                output_field=models.DateField(),
            ), output_field=models.DateField())
        )

        print(f'Updated {figures_to_convert_to_recommended_qs.count()} stock figures with role as recommended and the end date')
