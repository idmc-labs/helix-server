from django.core.management.base import BaseCommand
from django.db.models import F, Q
from openpyxl.workbook import Workbook
from apps.entry.models import Figure
from apps.event.models import Event
from apps.report.models import Report

# TODO:
# 1. Use distinct
# 2. Check for and/or conditions
# 3. Add triangulation

largest_date = '2022-01-01'
smallest_date = '1995-01-01'


def get_fact_url(id):
    if not id:
        return ''
    return f'https://helix.idmcdb.org/facts/{id}'


def get_event_url(id):
    if not id:
        return ''
    return f'https://helix.idmcdb.org/events/{id}'


def get_new_event_url(id):
    if not id:
        return ''
    return f'https://helix-alpha.idmcdb.org/events/{id}'


def add_row(workspace, row, *args):
    for index, arg in enumerate(args):
        if isinstance(arg, str) and (arg.startswith('https://') or arg.startswith('http://')):
            workspace.cell(row=row, column=index + 1).hyperlink = arg
        else:
            workspace.cell(row=row, column=index + 1).value = arg


settings = {
    'ws0': {
        'title': 'Summary',
        'code': 'Summary',
    },
    'ws1': {
        'title': f'Events with small/large event dates ({smallest_date} to {largest_date})',
        'code': 'E1',
    },
    'ws2': {
        'title': 'Recommended stock/flow figures without start date',
        'code': 'E2',
    },
    'ws3': {
        'title': 'Recommended flow figures without end date',
        'code': 'E3',
    },
    'ws4': {
        'title': 'Recommended stock figures without end reporting date',
        'code': 'E4',
    },
    'ws5': {
        'title': 'Recommended flow figures where start date greater than end date',
        'code': 'E5',
    },
    'ws6': {
        'title': 'Recommended stock figures where start date greater than end date',
        'code': 'E6',
    },
    'ws7': {
        'title': f'Recommended figures with small/large start/end dates ({smallest_date} to {largest_date})',
        'code': 'E7',
    },
    'ws8': {
        'title': 'Problematic reports where date range is not valid for recommended flow figures',
        'code': 'E8',
    },
}


class Command(BaseCommand):

    def handle(self, *args, **options):
        wb = Workbook()

        ws0 = wb.active

        # Events with small or large dates
        ws1 = wb.create_sheet(settings['ws1']['code'])
        ws1.append([settings['ws1']['title']])
        ws1.append(["Old ID", "Old URL", "ID", "URL"])

        # NOTE: start_date and end_date are required fields on database
        small_and_large_event_date_qs = Event.objects.filter(
            Q(start_date__gt=largest_date) |
            Q(start_date__lt=smallest_date) |
            Q(end_date__lt=smallest_date) |
            Q(end_date__gt=largest_date),
        ).distinct()

        events = list(small_and_large_event_date_qs.values('old_id', 'id'))
        for row, event in enumerate(events):
            add_row(
                ws1,
                row + 3,
                event["old_id"],
                get_event_url(event["old_id"]),
                event["id"],
                get_new_event_url(event["id"]),
            )

        # Recommended stock and flow figures without start date
        ws2 = wb.create_sheet(settings['ws2']['code'])
        ws2.append([settings['ws2']['title']])
        ws2.append(["Fact ID", "Fact URL"])

        start_date_null_figures_qs = Figure.objects.filter(
            start_date__isnull=True,
            role=Figure.ROLE.RECOMMENDED
        )

        old_ids = list(start_date_null_figures_qs.values_list('old_id', flat=True))
        for row, id in enumerate(old_ids):
            add_row(
                ws2,
                row + 3,
                id,
                get_fact_url(id),
            )

        # Recommended flow figures without end date
        ws3 = wb.create_sheet(settings['ws3']['code'])
        ws3.append([settings['ws3']['title']])
        ws3.append(["Fact ID", "Fact URL"])

        flow_figures_without_end_date_qs = Figure.objects.filter(
            end_date__isnull=True,
            category__type='Flow',
            role=Figure.ROLE.RECOMMENDED
        )

        old_ids = list(flow_figures_without_end_date_qs.values_list('old_id', flat=True))
        for row, id in enumerate(old_ids):
            add_row(
                ws2,
                row + 3,
                id,
                get_fact_url(id),
            )

        # Recommended stock figures without end date
        ws4 = wb.create_sheet(settings['ws4']['code'])
        ws4.append([settings['ws4']['title']])
        ws4.append(["Fact ID", "Fact URL"])

        stock_figures_without_end_date_qs = Figure.objects.filter(
            end_date__isnull=True,
            category__type='Stock',
            role=Figure.ROLE.RECOMMENDED
        )

        old_ids = list(stock_figures_without_end_date_qs.values_list('old_id', flat=True))
        for row, id in enumerate(old_ids):
            add_row(
                ws4,
                row + 3,
                id,
                get_fact_url(id),
            )

        # Recommended flow figures where start date is greater than end date
        ws5 = wb.create_sheet(settings['ws5']['code'])
        ws5.append([settings['ws5']['title']])
        ws5.append(["Fact ID", "Fact URL"])

        flow_figures_with_start_date_gt_end_date_qs = Figure.objects.filter(
            start_date__is_null=False,
            end_date__is_null=False,
            start_date__gt=F('end_date'),
            category__type='Flow',
            role=Figure.ROLE.RECOMMENDED
        )

        old_ids = list(flow_figures_with_start_date_gt_end_date_qs.values_list('old_id', flat=True))
        for row, id in enumerate(old_ids):
            add_row(
                ws5,
                row + 3,
                id,
                get_fact_url(id),
            )

        # Recommended stock figures where start date is greater than end date
        ws6 = wb.create_sheet(settings['ws6']['code'])
        ws6.append([settings['ws6']['title']])
        ws6.append(["Fact ID", "Fact URL"])

        stock_figures_with_start_date_gt_end_date_qs = Figure.objects.filter(
            start_date__is_null=False,
            end_date__is_null=False,
            start_date__gt=F('end_date'),
            category__type='Stock',
            role=Figure.ROLE.RECOMMENDED
        )

        old_ids = list(stock_figures_with_start_date_gt_end_date_qs.values_list('old_id', flat=True))
        for row, id in enumerate(old_ids):
            add_row(
                ws6,
                row + 3,
                id,
                get_fact_url(id),
            )

        # Recommended stock and flow figures with small or large dates
        ws7 = wb.create_sheet(settings['ws7']['code'])
        ws7.append([settings['ws7']['title']])
        ws7.append(["Fact ID", "Fact URL"])

        small_and_large_figure_date_qs = Figure.objects.filter(
            Q(start_date__gt=largest_date) |
            Q(start_date__lt=smallest_date) |
            Q(end_date__gt=largest_date) |
            Q(end_date__lt=smallest_date),
            role=Figure.ROLE.RECOMMENDED
        ).distinct()

        old_ids = list(small_and_large_figure_date_qs.values_list('old_id', flat=True))
        for row, id in enumerate(old_ids):
            add_row(
                ws7,
                row + 3,
                id,
                get_fact_url(id),
            )

        # Masterfacts with flow figures not included in report
        ws8 = wb.create_sheet(settings['ws8']['code'])
        ws8.append([settings['ws8']['title']])
        ws8.append(["Fact ID", "Fact URL"])

        problematic_reports_qs = Report.objects.filter(
            filter_figure_start_after__gt=F('figures__start_date'),
            filter_figure_end_before__lt=F('figures__end_date'),
            figures__category__type='Flow',
            figures__role=Figure.ROLE.RECOMMENDED,
        ).distinct()

        row = 3
        for obj in problematic_reports_qs:
            problematic_figures = obj.figures.filter(
                start_date__lt=obj.filter_figure_start_after,
                end_date__gt=obj.filter_figure_end_before
            )
            for problematic_figure in problematic_figures:
                add_row(
                    ws8,
                    row,
                    obj.old_id,
                    get_fact_url(obj.old_id) if obj.old_id.isnumeric() else '',
                    get_fact_url(problematic_figure.old_id),
                )
                row = row + 1

        # Summary page
        ws0.title = "summary"
        ws0.append(["Code", "Title", "Count"])
        ws0.append([settings['ws1']['code'], settings['ws1']['title'], small_and_large_event_date_qs.count()])
        ws0.append([settings['ws2']['code'], settings['ws2']['title'], start_date_null_figures_qs.count()])
        ws0.append([settings['ws3']['code'], settings['ws3']['title'], flow_figures_without_end_date_qs.count()])
        ws0.append([settings['ws4']['code'], settings['ws4']['title'], stock_figures_without_end_date_qs.count()])
        ws0.append([settings['ws5']['code'], settings['ws5']['title'], flow_figures_with_start_date_gt_end_date_qs.count()])
        ws0.append([settings['ws6']['code'], settings['ws6']['title'], stock_figures_with_start_date_gt_end_date_qs.count()])
        ws0.append([settings['ws7']['code'], settings['ws7']['title'], small_and_large_figure_date_qs.count()])
        ws0.append([settings['ws8']['code'], settings['ws8']['title'], problematic_reports_qs.count()])

        wb.save(filename="data-errors.xlsx")
