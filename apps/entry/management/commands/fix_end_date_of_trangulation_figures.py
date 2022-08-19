from django.core.management.base import BaseCommand
from django.db.models import F
from apps.entry.models import Figure
from datetime import date


class Command(BaseCommand):
    help = 'Fix end date of trangulation figires'

    def handle(self, *args, **options):
        trangulation_figures_with_null_end_date = Figure.objects.filter(
            role=Figure.ROLE.TRIANGULATION,
            end_date__isnull=True,
            start_date__isnull=False,
        )
        # Update end_date with start date
        trangulation_figures_with_null_end_date.update(end_date=F('start_date'))
        print(f'Updated {trangulation_figures_with_null_end_date.count()} figures end_date with start_date')

        # There are few figures having null start date as well as end date
        # In this case we make start_date, end_date from year field in old db
        trangulation_figures_with_null_start_date_map = {
            '169': 2016,
            '342': 2016,
            '444': 2016,
            '2257': 2016,
            '3291': 2016,
            '4154': 2017,
            '4297': 2017,
            '4597': 2017,
            '4598': 2017,
            '4833': 2017,
            '4846': 2017,
            '5424': 2017,
            '6154': 2017,
            '6302': 2017,
            '6310': 2017,
            '6345': 2017,
            '7502': 2017,
            '7554': 2017,
            '7646': 2017,
            '7677': 2017,
        }
        figures_to_update = Figure.objects.filter(
            role=Figure.ROLE.TRIANGULATION,
            end_date__isnull=True,
            start_date__isnull=True,
        )
        for figure in figures_to_update:
            year = trangulation_figures_with_null_start_date_map.get(figure.old_id, None),
            if year:
                figure.start_date = date(year=year, month=1, day=1)
                figure.end_date = figure.start_date

        Figure.objects.bulk_update(figures_to_update, ['start_date', 'end_date'])
        print(f'Updated {figures_to_update.count()} figures start_date and end_date with start_date')
