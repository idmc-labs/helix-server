import csv
import json
from uuid import uuid4
import copy
from django.core.management.base import BaseCommand
from apps.entry.models import Figure
from django.db.models.functions import Concat, Cast
from django.db import models, transaction


class Command(BaseCommand):
    help = 'Fix stock disaster figures for 2019 and 2022'

    def add_arguments(self, parser):
        parser.add_argument('csv_file')

    @transaction.atomic
    def handle(self, *args, **options):
        csv_file = options['csv_file']

        with open(csv_file, 'r') as csv_file:
            rows = csv.DictReader(csv_file)

            figures_to_clone_as_stock = []
            figures_to_convert_to_recommended = []

            for row in rows:
                if row['ids']:
                    figures = json.loads(row['ids'])
                    status = row['status']
                    if status == 'One figure returned':
                        figure = figures[0]
                        if figure["category"] == 6:
                            figures_to_clone_as_stock.append(figure['id'])
                        elif figure["category"] == 0 and figure["role"] == 1:
                            figures_to_convert_to_recommended.append(figure["id"])
                    elif status == 'Two figures returned and one figure is stock and the other is ND':
                        figure = figures[0] if figures[0]["category"] == 0 else figures[1]
                        if figure["role"] == 1:
                            figures_to_convert_to_recommended.append(figure["id"])

            figures_to_convert_to_recommended_qs = Figure.objects.filter(
                id__in=figures_to_convert_to_recommended,
            )
            figures_to_convert_to_recommended_qs.update(
                role=Figure.ROLE.RECOMMENDED,
                end_date=Cast(Concat(
                    'start_date__year',
                    models.Value('-12-31'),
                    output_field=models.DateField(),
                ), output_field=models.DateField())
            )

            for figure_id in figures_to_convert_to_recommended_qs.values_list('id', flat=True):
                print(f'Updated stock figure {figure_id} with role as recommended and the end date')

            # Make a list of figures that were converted to recommended
            print(f'Updated {figures_to_convert_to_recommended_qs.count()} stock figures with role as recommended and the end date')

            # Clone figures_to_clone_as_stock and update end_date as last day of year of start date
            success = 0
            for figure in Figure.objects.filter(
                id__in=figures_to_clone_as_stock
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
                print(f'Cloned flow figure {figure.id} as stock figure {new_figure.id}')

            # Make a list of new figures that were cloned (clear old_id when cloning or we are going to have a bad time)
            print(f'Cloned {success} flow figures as stock figures')
