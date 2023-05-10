import csv
import logging
import copy
from uuid import uuid4
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.entry.models import Figure

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Clone flow figure figures to stock figures"

    def add_arguments(self, parser):
        parser.add_argument('figures')

    @transaction.atomic
    def handle(self, *args, **kwargs):
        figures_file = kwargs['figures']

        with open(figures_file, 'r') as figures_csv_file:
            reader = csv.DictReader(figures_csv_file)
            ids = [figure['id'] for figure in reader]

        success = 0
        for figure in Figure.objects.filter(
            id__in=ids
        ):
            new_figure = copy.deepcopy(figure)

            new_figure.id = None
            new_figure.old_id = None
            new_figure.uuid = uuid4()
            year = int(new_figure.start_date.year)
            end_date = f'{year}-12-31'
            new_figure.end_date = end_date
            new_figure.role = Figure.ROLE.RECOMMENDED
            new_figure.category = Figure.FIGURE_CATEGORY_TYPES.IDPS
            new_figure.was_subfact = False
            new_figure.approved_by = None
            new_figure.approved_on = None
            new_figure.review_status = Figure.FIGURE_REVIEW_STATUS.REVIEW_NOT_STARTED
            new_figure.save()

            geo_locations_list = []
            for geo_location in figure.geo_locations.all():
                geo_location.id = None
                geo_location.uuid = uuid4()
                geo_location.save()
                geo_locations_list.append(geo_location)
            new_figure.geo_locations.set(geo_locations_list)

            new_figure.sources.set(figure.sources.all())
            new_figure.tags.set(figure.tags.all())
            new_figure.context_of_violence.set(figure.context_of_violence.all())

            disaggregation_age_list = []
            for disaggregation_age in figure.disaggregation_age.all():
                disaggregation_age.id = None
                disaggregation_age.uuid = uuid4()
                disaggregation_age.save()
                disaggregation_age_list.append(disaggregation_age)
            new_figure.disaggregation_age.set(disaggregation_age_list)

            success += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'Cloned flow figure {figure.id} as stock figure {new_figure.id}'
                )
            )

        # Make a list of new figures that were cloned (clear old_id when cloning or we are going to have a bad time)
        self.stdout.write(
            self.style.SUCCESS(
                f'Cloned {success} flow figures as stock figures'
            )
        )
