from django.core.management.base import BaseCommand
from django.db.models import F
from apps.entry.models import Figure
from datetime import date


class Command(BaseCommand):
    help = 'Fix stock disaster figures for 2019 and 2022'

    def handle(self, *args, **options):
        figures_to_clone_as_stock = []
        figures_to_convert_to_recommended = []

        # TODO: read rows from csv

        for row in rows:
            figures = row['ids']
            status = row['status']
            if status == 'One figure returned':
                figure = figures[0]
                if figure.category == 6:
                    figures_to_clone_as_stock.append(figure.id)
                elif figure.category == 0 and figure.role == 1:
                    figures_to_convert_to_recommended.append(figure.id)
            elif status == 'Two figures returned and one figure is stock and the other is ND':
                figure = figures[0] if figures[0].category == 0 else figures[1]
                if figure.role == 1:
                    figures_to_convert_to_recommended.append(figure.id)

        print(figures_to_clone_as_stock)
        print(figures_to_convert_to_recommended)

        figures_to_convert_to_recommended_qs = Figure.objects.filter(
            id___in=figures_to_convert_to_recommended,
            end_date__isnull=True,
            start_date__isnull=False,
        )
        figures_to_convert_to_recommended_qs.update(role=Figure.ROLE.TRIANGULATION)

        print(f'Updated {figures_to_convert_to_recommended_qs.count()} figures as triangulation')

        # TODO: clone figures_to_clone_as_stock and update end_date as last day of year of start date

        # TODO: make a list of figures that were converted to recommended
        # TODO: make a list of new figures that were cloned (clear old_id when cloning or we are going to have a bad time)
