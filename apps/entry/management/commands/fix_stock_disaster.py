import csv
import json
from django.core.management.base import BaseCommand
from django.db.models import F
from apps.entry.models import Figure
from datetime import date


class Command(BaseCommand):
    help = 'Fix stock disaster figures for 2019 and 2022'

    def add_arguments(self, parser):
        parser.add_argument('csv_file')

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
                end_date__isnull=True,
                start_date__isnull=False,
            )
            figures_to_convert_to_recommended_qs.update(role=Figure.ROLE.RECOMMENDED)

            # Make a list of figures that were converted to recommended
            print(
                f'Updated {figures_to_convert_to_recommended_qs.count()} figures as recommended',
                figures_to_convert_to_recommended_qs.values('id')
            )

            # Clone figures_to_clone_as_stock and update end_date as last day of year of start date
            figures_cloned_list = []
            for figure in Figure.objects.filter(
                id__in=figures_to_clone_as_stock
            ):
                figure.id = None
                figure.old_id = None
                year = int(figure.start_date.year)
                end_date = f'{year}-12-31'
                figure.end_date = end_date
                figure.role = Figure.ROLE.RECOMMENDED
                figure.save()

                # TODO: Also clone disaggregatedage and osmname relations
                # figure.geo_locations.__dict__;
                # figure.disaggregation_age.__dict__;

                figures_cloned_list.append(figure.id)

            # Make a list of new figures that were cloned (clear old_id when cloning or we are going to have a bad time)
            print(
                f'Cloned {len(figures_cloned_list)} figures',
                figures_cloned_list,
            )
