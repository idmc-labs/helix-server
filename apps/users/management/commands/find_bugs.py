from django.core.management.base import BaseCommand
from apps.entry.models import Figure
from apps.event.models import Event
from django.db.models import F, Q
from apps.report.models import Report

class Command(BaseCommand):
    def handle(self, *args, **options):
        file = open("data_errors.txt", "a")  # append mode

        # Recommended stock and flow figures without start date
        start_date_null_figures = Figure.objects.filter(
            start_date__isnull=True,
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(start_date_null_figures.values_list('old_id', flat=True))
        file.write(f'1. Recommended stock/flow figures without start date: {start_date_null_figures.count()}\n')
        file.write(f'OLD IDS: {old_ids}\n\n')

        # Recommended flow figures without end date
        flow_figures_without_end_date = Figure.objects.filter(
            end_date__isnull=True,
            category__type='Flow',
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(flow_figures_without_end_date.values_list('old_id', flat=True))
        file.write(f'2. Recommended flow figures without end date: {flow_figures_without_end_date.count()}\n')
        file.write(f'OLD IDS: {old_ids}\n\n')

        # Recommended stock figures without end date
        stock_figures_without_end_date = Figure.objects.filter(
            end_date__isnull=True,
            category__type='Stock',
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(stock_figures_without_end_date.values_list('old_id', flat=True))
        file.write(f'3. Recommended stock figures without end reporting date: {stock_figures_without_end_date.count()}\n')
        file.write(f'OLD IDS: {old_ids}\n\n')

        # Recommended flow figures where start date is greater than end date
        stock_figures_with_start_date_gte_end_date = Figure.objects.filter(
            start_date__gte=F('end_date'),
            category__type='Flow',
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(stock_figures_with_start_date_gte_end_date.values_list('old_id', flat=True))
        file.write(f'4. Recommended flow figures where start date greater than end date: {stock_figures_with_start_date_gte_end_date.count()}\n')
        file.write(f'OLD IDS: {old_ids}\n\n')

        # Recommended stock figures where start date is greater than end date
        stock_figures_with_start_date_gte_end_date = Figure.objects.filter(
            start_date__gte=F('end_date'),
            category__type='Stock',
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(stock_figures_with_start_date_gte_end_date.values_list('old_id', flat=True))
        file.write(f'5. Recommended stock figures where start date greater than end date: {stock_figures_with_start_date_gte_end_date.count()}\n')
        file.write(f'OLD IDS: {old_ids}\n\n')

        # Events with small or large dates
        largest_date = '2022-01-01'
        smallest_date = '1995-01-01'
        small_and_large_event_date = Event.objects.filter(
            Q(start_date__gte=largest_date) |
            Q(start_date__lte=smallest_date) |
            Q(end_date__lte=smallest_date) |
            Q(end_date__gte=largest_date)
        )

        old_ids = list(small_and_large_event_date.values('old_id', 'id'))
        file.write(f'6. Events with small and large event dates ({smallest_date} to {largest_date}): {small_and_large_event_date.count()}\n')
        file.write(f'IDS: {old_ids}\n\n')

        # Recommended stock and flow figures with small or large dates
        small_and_large_figure_date = Figure.objects.filter(
            Q(start_date__gte=largest_date) |
            Q(start_date__lte=smallest_date) |
            Q(end_date__gte=largest_date),
            Q(end_date__lte=smallest_date),
            role=Figure.ROLE.RECOMMENDED
        ).distinct()
        old_ids = list(small_and_large_figure_date.values_list('old_id', flat=True))
        file.write(f'7. Recommended figures with small and large start/end dates ({smallest_date} to {largest_date}): {small_and_large_figure_date.count()}\n')
        file.write(f'OLD IDS: {old_ids}\n\n')

        # Masterfacts with flow figures not included in report
        problematic_reports = Report.objects.filter(
            filter_figure_start_after__gte=F('figures__start_date'),
            filter_figure_end_before__lte=F('figures__end_date'),
            figures__category__type='Flow',
            figures__role=Figure.ROLE.RECOMMENDED,
        ).distinct()
        file.write(f'8. Problematic reports where date range is not valid for figures=> {problematic_reports.count()}\n')
        ids = list(problematic_reports.values('old_id', 'id'))
        file.write(f'Problematic report IDS => {ids}\n\n')

        file.close()
