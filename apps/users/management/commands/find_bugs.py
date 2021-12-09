from django.core.management.base import BaseCommand
from apps.entry.models import Figure
from apps.event.models import Event
from django.db.models import F, Q
from apps.report.models import Report
from openpyxl.workbook import Workbook

class Command(BaseCommand):
    def handle(self, *args, **options):


        wb = Workbook()

        ws1 = wb.create_sheet('Recommended stock or flow figures without start date')
        ws2 = wb.create_sheet('Recommended flow figures without end date')
        ws3 = wb.create_sheet('Recommended stock figures without end reporting date')
        ws4 = wb.create_sheet('Recommended flow figures where start date greater than end date')
        ws5 = wb.create_sheet('Recommended stock figures where start date greater than end date')
        ws6 = wb.create_sheet('Events with small and large event dates')
        ws7 = wb.create_sheet('Recommended figures with small and large start or end dates')
        ws8 = wb.create_sheet('Problematic reports where date range is not valid for figures')

        wb.active.append(["SN", "Error title", "Counts"])

        # Recommended stock and flow figures without start date
        start_date_null_figures = Figure.objects.filter(
            start_date__isnull=True,
            role=Figure.ROLE.RECOMMENDED
        )
        error_title = f'Recommended stock/flow figures without start date'
        wb.active.append([1, error_title, start_date_null_figures.count()])
        old_ids = list(start_date_null_figures.values_list('old_id', flat=True))
        ws1.append(["Fact ID", "Fact URL"])
        for id in old_ids:
            ws1.append([id, f'https://helix.idmcdb.org/facts/{id}'])

        # Recommended flow figures without end date
        flow_figures_without_end_date = Figure.objects.filter(
            end_date__isnull=True,
            category__type='Flow',
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(flow_figures_without_end_date.values_list('old_id', flat=True))
        error_title = 'Recommended flow figures without end date'
        wb.active.append([2, error_title, flow_figures_without_end_date.count()])
        ws2.append(["Fact ID", "Fact URL"])
        for id in old_ids:
            ws2.append([id, f'https://helix.idmcdb.org/facts/{id}'])


        # Recommended stock figures without end date
        stock_figures_without_end_date = Figure.objects.filter(
            end_date__isnull=True,
            category__type='Stock',
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(stock_figures_without_end_date.values_list('old_id', flat=True))
        error_title = 'Recommended stock figures without end reporting date'
        wb.active.append([3, error_title, stock_figures_without_end_date.count()])
        ws3.append(["Fact ID", "Fact URL"])
        for id in old_ids:
            ws3.append([id, f'https://helix.idmcdb.org/facts/{id}'])


        # Recommended flow figures where start date is greater than end date
        stock_figures_with_start_date_gte_end_date = Figure.objects.filter(
            start_date__gte=F('end_date'),
            category__type='Flow',
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(stock_figures_with_start_date_gte_end_date.values_list('old_id', flat=True))
        error_title = 'Recommended flow figures where start date greater than end date'
        wb.active.append([4, error_title, stock_figures_with_start_date_gte_end_date.count()])
        ws4.append(["Fact ID", "Fact URL"])
        for id in old_ids:
            ws4.append([id, f'https://helix.idmcdb.org/facts/{id}'])


        # Recommended stock figures where start date is greater than end date
        stock_figures_with_start_date_gte_end_date = Figure.objects.filter(
            start_date__gte=F('end_date'),
            category__type='Stock',
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(stock_figures_with_start_date_gte_end_date.values_list('old_id', flat=True))
        error_title = 'Recommended stock figures where start date greater than end date'
        wb.active.append([5, error_title, stock_figures_with_start_date_gte_end_date.count()])
        ws5.append(["Fact ID", "Fact URL"])
        for id in old_ids:
            ws5.append([id, f'https://helix.idmcdb.org/facts/{id}'])


        # Events with small or large dates
        largest_date = '2022-01-01'
        smallest_date = '1995-01-01'
        small_and_large_event_date = Event.objects.filter(
            Q(start_date__gte=largest_date) |
            Q(start_date__lte=smallest_date) |
            Q(end_date__lte=smallest_date) |
            Q(end_date__gte=largest_date)
        )

        event_objects = list(small_and_large_event_date.values('old_id', 'id'))
        error_title = f'Events with small and large event dates ({smallest_date} to {largest_date})'
        wb.active.append([6, error_title, small_and_large_event_date.count()])
        ws6.append(["Old Id", "ID", "Old URL", "New URL"])
        for event_object in event_objects:
            ws6.append([event_object["old_id"], event_object["id"], f'https://helix.idmcdb.org/events/{event_object["old_id"]}', f'https://helix-alpha.idmcdb.org/events/{event_object["id"]}'])


        # Recommended stock and flow figures with small or large dates
        small_and_large_figure_date = Figure.objects.filter(
            Q(start_date__gte=largest_date) |
            Q(start_date__lte=smallest_date) |
            Q(end_date__gte=largest_date),
            Q(end_date__lte=smallest_date),
            role=Figure.ROLE.RECOMMENDED
        ).distinct()
        old_ids = list(small_and_large_figure_date.values_list('old_id', flat=True))
        error_title = f'Recommended figures with small and large start/end dates ({smallest_date} to {largest_date})'
        wb.active.append([7, error_title, small_and_large_figure_date.count()])
        ws7.append(["Fact ID", "Fact URL"])
        for id in old_ids:
            ws5.append([id, f'https://helix.idmcdb.org/facts/{id}'])


        # Masterfacts with flow figures not included in report
        problematic_reports = Report.objects.filter(
            filter_figure_start_after__gte=F('figures__start_date'),
            filter_figure_end_before__lte=F('figures__end_date'),
            figures__category__type='Flow',
            figures__role=Figure.ROLE.RECOMMENDED,
        ).distinct()
        error_title = 'Problematic reports where date range is not valid for figures'
        report_ids = list(problematic_reports.values_list('id', flat=True))
        wb.active.append([8, error_title, problematic_reports.count()])
        ws7.append(["Report ID", "Report URL"])
        for id in report_ids:
            ws7.append([id, f'https://helix-alpha.idmcdb.org/reports/{id}/'])


        wb.save(filename="data-errors.xlsx")
