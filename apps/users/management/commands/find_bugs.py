from django.core.management.base import BaseCommand
from apps.entry.models import Figure
from apps.event.models import Event
from django.db.models import F, Q

class Command(BaseCommand):
    def handle(self, *args, **options):
        file = open("data_errors.txt", "a")  # append mode

        start_date_null_figures = Figure.objects.filter(
            start_date__isnull=True,
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(start_date_null_figures.values_list('old_id', flat=True))
        file.write(f'1. Total recommended stock/flow figures without start date => {start_date_null_figures.count()}\n')
        file.write(f'OLD IDS => {old_ids}\n\n')


        flow_figures_without_end_date = Figure.objects.filter(
            end_date__isnull=True, category__type='Flow',
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(flow_figures_without_end_date.values_list('old_id', flat=True))
        file.write(f'2. Total recommended flow figures without end date => {flow_figures_without_end_date.count()}\n')
        file.write(f'OLD IDS => {old_ids}\n\n')


        stock_figures_without_end_date = Figure.objects.filter(
            end_date__isnull=True,
            category__type='Stock',
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(stock_figures_without_end_date.values_list('old_id', flat=True))
        file.write(f'3. Recommended stock figures without end reporting date => {stock_figures_without_end_date.count()}\n')
        file.write(f'OLD IDS => {old_ids}\n\n')


        stock_figures_with_start_date_lte_end_date = Figure.objects.filter(
            start_date__lte=F('end_date'),
            category__type='Flow',
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(stock_figures_with_start_date_lte_end_date.values_list('old_id', flat=True))
        file.write(f'4. Recommended flow figures where start date < end date => {stock_figures_with_start_date_lte_end_date.count()}\n')
        file.write(f'OLD IDS => {old_ids}\n\n')


        stock_figures_with_start_date_lte_end_date = Figure.objects.filter(
            start_date__lte=F('end_date'),
            category__type='Stock',
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(stock_figures_with_start_date_lte_end_date.values_list('old_id', flat=True))
        file.write(f'5. Recommended stock figures where start date < end date => {stock_figures_with_start_date_lte_end_date.count()}\n')
        file.write(f'OLD IDS => {old_ids}\n\n')


        small_and_large_event_date = Event.objects.filter(Q(
            start_date__gte='2022-01-01') | Q(end_date__lte='1995-01-01')
        )
        old_ids = list(small_and_large_event_date.values('old_id', 'id'))
        file.write(f'6. Small and large event dates (1995-01-01 to 2022-01-01) => {small_and_large_event_date.count()}\n')
        file.write(f'IDS => {old_ids}\n\n')


        small_and_large_figure_date = Figure.objects.filter(
            Q(start_date__gte='2022-01-01') | Q(end_date__lte='1995-01-01'), \
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(small_and_large_figure_date.values_list('old_id', flat=True))
        file.write(f'7. Small and large recommended figure dates (1995-01-01 to 2022-01-01) => {small_and_large_figure_date.count()}\n')
        file.write(f'OLD IDS => {old_ids}\n\n')

        file.close()
