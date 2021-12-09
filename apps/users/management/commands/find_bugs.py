from django.core.management.base import BaseCommand
from apps.entry.models import Figure
from apps.event.models import Event
from django.db.models import F, Q
from apps.report.models import Report
from openpyxl.workbook import Workbook

class Command(BaseCommand):

    def handle(self, *args, **options):


        wb = Workbook()

        ws1 = wb.create_sheet('E1')
        ws2 = wb.create_sheet('E2')
        ws3 = wb.create_sheet('E3')
        ws4 = wb.create_sheet('E4')
        ws5 = wb.create_sheet('E5')
        ws6 = wb.create_sheet('E6')
        ws7 = wb.create_sheet('E7')
        ws8 = wb.create_sheet('E8')
        wb.active.title = "summary"
        wb.active.append(["SN", "Error title", "Counts"])

        # Recommended stock and flow figures without start date
        start_date_null_figures = Figure.objects.filter(
            start_date__isnull=True,
            role=Figure.ROLE.RECOMMENDED
        )
        error_title = f'Recommended stock/flow figures without start date'
        wb.active.append([1, error_title, start_date_null_figures.count()])
        old_ids = list(start_date_null_figures.values_list('old_id', flat=True))
        ws1.append([error_title])
        ws1.append(["Fact ID", "Fact URL"])
        row = 3
        for id in old_ids:
            link = f'https://helix.idmcdb.org/facts/{id}'
            ws1.cell(row=row, column=1).value = (id)
            ws1.cell(row=row, column=2).hyperlink = (link)
            row = row + 1

        # Recommended flow figures without end date
        flow_figures_without_end_date = Figure.objects.filter(
            end_date__isnull=True,
            category__type='Flow',
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(flow_figures_without_end_date.values_list('old_id', flat=True))
        error_title = 'Recommended flow figures without end date'
        wb.active.append([2, error_title, flow_figures_without_end_date.count()])
        ws2.append([error_title])
        ws2.append(["Fact ID", "Fact URL"])
        row = 3
        for id in old_ids:
            link = f'https://helix.idmcdb.org/facts/{id}'
            ws2.cell(row=row, column=1).value = (id)
            ws2.cell(row=row, column=2).hyperlink = (link)
            row = row + 1


        # Recommended stock figures without end date
        stock_figures_without_end_date = Figure.objects.filter(
            end_date__isnull=True,
            category__type='Stock',
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(stock_figures_without_end_date.values_list('old_id', flat=True))
        error_title = 'Recommended stock figures without end reporting date'
        wb.active.append([3, error_title, stock_figures_without_end_date.count()])
        ws3.append([error_title])
        ws3.append(["Fact ID", "Fact URL"])
        row = 3
        for id in old_ids:
            link = f'https://helix.idmcdb.org/facts/{id}'
            ws3.cell(row=row, column=1).value = (id)
            ws3.cell(row=row, column=2).hyperlink = (link)
            row = row + 1

        # Recommended flow figures where start date is greater than end date
        stock_figures_with_start_date_gte_end_date = Figure.objects.filter(
            start_date__gte=F('end_date'),
            category__type='Flow',
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(stock_figures_with_start_date_gte_end_date.values_list('old_id', flat=True))
        error_title = 'Recommended flow figures where start date greater than end date'
        wb.active.append([4, error_title, stock_figures_with_start_date_gte_end_date.count()])
        ws4.append([error_title])
        ws4.append(["Fact ID", "Fact URL"])
        row = 3
        for id in old_ids:
            link = f'https://helix.idmcdb.org/facts/{id}'
            ws4.cell(row=row, column=1).value = (id)
            ws4.cell(row=row, column=2).hyperlink = (link)
            row = row + 1

        # Recommended stock figures where start date is greater than end date
        stock_figures_with_start_date_gte_end_date = Figure.objects.filter(
            start_date__gte=F('end_date'),
            category__type='Stock',
            role=Figure.ROLE.RECOMMENDED
        )
        old_ids = list(stock_figures_with_start_date_gte_end_date.values_list('old_id', flat=True))
        error_title = 'Recommended stock figures where start date greater than end date'
        wb.active.append([5, error_title, stock_figures_with_start_date_gte_end_date.count()])
        ws5.append([error_title])
        ws5.append(["Fact ID", "Fact URL"])
        row = 3
        for id in old_ids:
            link = f'https://helix.idmcdb.org/facts/{id}'
            ws5.cell(row=row, column=1).value = (id)
            ws5.cell(row=row, column=2).hyperlink = (link)
            row = row + 1

        # Events with small or large dates
        largest_date = '2022-01-01'
        smallest_date = '1995-01-01'
        small_and_large_event_date = Event.objects.filter(
            Q(start_date__gte=largest_date) |
            Q(start_date__lte=smallest_date) |
            Q(end_date__lte=smallest_date) |
            Q(end_date__gte=largest_date),
            Q(start_date__isnull=False) |
            Q(start_date__isnull=False),
        )

        event_objects = list(small_and_large_event_date.values('old_id', 'id'))
        error_title = f'Events with small and large event dates ({smallest_date} to {largest_date})'
        wb.active.append([6, error_title, small_and_large_event_date.count()])
        ws6.append([error_title])
        ws6.append(["Old Id", "ID", "Old URL", "New URL"])
        row = 3
        for event_object in event_objects:
            new_event_url = f'https://helix-alpha.idmcdb.org/events/{event_object["id"]}'
            old_event_url = f'https://helix.idmcdb.org/events/{event_object["old_id"]}' if event_object["old_id"] else ""
            ws6.cell(row=row, column=1).value = (event_object["old_id"])
            ws6.cell(row=row, column=2).value = (event_object["old_id"])
            ws6.cell(row=row, column=3).hyperlink = (old_event_url)
            ws6.cell(row=row, column=4).hyperlink = (new_event_url)
            row = row + 1

        # Recommended stock and flow figures with small or large dates
        small_and_large_figure_date = Figure.objects.filter(
            Q(start_date__gte=largest_date) |
            Q(start_date__lte=smallest_date) |
            Q(end_date__gte=largest_date),
            Q(end_date__lte=smallest_date),
            Q(start_date__isnull=False) |
            Q(start_date__isnull=False),
            role=Figure.ROLE.RECOMMENDED
        ).distinct()
        old_ids = list(small_and_large_figure_date.values_list('old_id', flat=True))
        error_title = f'Recommended figures with small and large start/end dates ({smallest_date} to {largest_date})'
        wb.active.append([7, error_title, small_and_large_figure_date.count()])
        ws7.append([error_title])
        ws7.append(["Fact ID", "Fact URL"])
        row = 3
        for id in old_ids:
            link = f'https://helix.idmcdb.org/facts/{id}'
            ws7.cell(row=row, column=1).value = (id)
            ws7.cell(row=row, column=2).hyperlink = (link)
            row = row + 1


        # Masterfacts with flow figures not included in report
        problematic_reports = Report.objects.filter(
            filter_figure_start_after__gte=F('figures__start_date'),
            filter_figure_end_before__lte=F('figures__end_date'),
            figures__category__type='Flow',
            figures__role=Figure.ROLE.RECOMMENDED,
        ).distinct()
        error_title = 'Problematic reports where date range is not valid for figures'
        wb.active.append([8, error_title, problematic_reports.count()])
        ws8.append([error_title])
        ws8.append(["Old ID", "Old Report URL", "Problematic figure"])
        row = 3
        for obj in problematic_reports:
            problematic_figures = obj.figures.filter(
                start_date__lte=obj.filter_figure_start_after,
                end_date__gte=obj.filter_figure_end_before
            )
            problematic_figures_links = []
            for problematic_figure in problematic_figures:
                report_url = f'https://helix.idmcdb.org/facts/{obj.old_id}' if obj.old_id else ""
                problematic_figure_url = f'https://helix.idmcdb.org/facts/{problematic_figure.old_id}' if problematic_figure.old_id else ""
                ws8.cell(row=row, column=1).value = (obj.old_id)
                ws8.cell(row=row, column=2).hyperlink = (report_url)
                ws8.cell(row=row, column=3).hyperlink = (problematic_figure_url)
                row = row + 1

        wb.save(filename="data-errors.xlsx")
