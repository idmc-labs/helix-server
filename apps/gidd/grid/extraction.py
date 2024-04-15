import os
import datetime

from openpyxl import Workbook
from openpyxl.writer.excel import save_virtual_workbook
from django.db import models
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models.functions import Coalesce, ExtractYear

from utils.common import load_csv
from common.utils import EXTERNAL_ARRAY_SEPARATOR
from apps.event.models import Figure, Event
from apps.country.models import Country
from apps.crisis.models import Crisis


def noop(val):
    return val


def enum_list_render(values, resolver=None):
    if resolver:
        return EXTERNAL_ARRAY_SEPARATOR.join([
            resolver(v)
            for v in values or []
            if v is not None
        ])
    return EXTERNAL_ARRAY_SEPARATOR.join([
        v.label for v in values or []
        if v is not None
    ])


def category_enum_list_render(values):
    def _resolver(v):
        if v in ['Internal Displacements', 'IDPs']:
            return v
        return Figure.FIGURE_CATEGORY_TYPES(v).label
    if type(values) is list:
        return enum_list_render(values, resolver=_resolver)
    return enum_list_render([values], resolver=_resolver)


def cause_enum_list_render(values):
    def _resolver(v):
        if v in ['Disaster', 'Conflict']:
            return v
        return Crisis.CRISIS_TYPE(v).label

    if type(values) is list:
        return enum_list_render(values, resolver=_resolver)
    return enum_list_render([values], resolver=_resolver)


def str_list_render(values):
    return EXTERNAL_ARRAY_SEPARATOR.join([
        value for value in values or []
        if value is not None
    ])


def run_csv(generator, year):
    headers, data = generator(year)
    rows = [
        list(headers.keys()),
    ]

    for datum in data:
        rows.append([
            parser(datum[key])
            for key, parser in headers.items()
        ])
    return rows


def get_geographic_regions_query(country_field):
    # https://github.com/idmc-labs/helix2.0-meta/issues/317#issuecomment-1476575483
    return models.Case(
        models.When(
            **{
                f"{country_field}__geographical_group__name__in": [
                    'Latin America and the Caribbean',
                    'North America',
                ],
            },
            then=models.Value('The Americas', output_field=models.CharField()),
        ),
        default=models.F(f"{country_field}__geographical_group__name"),
    )


def tab_1(gidd_year):
    headers = {
        'Geographic Regions': (get_geographic_regions_query('country'), noop),
        'ISO3': (models.F('country__iso3'), noop),
        'Country': (models.F('country__idmc_short_name'), noop),
        'Year': (models.F('year'), noop),
        # NEW
        'Figure Cause': (models.F('figure_cause'), cause_enum_list_render),
        'Figure Category': (models.F('category'), category_enum_list_render),
        'Cause Category': (models.F('cause_category'), noop),
        'Cause Type': (models.F('cause_type'), noop),
        'Cause Subtype': (models.F('cause_subtype'), noop),
        # FIGURES
        'Total Figures': (models.F('total_total_figures'), noop),
    }

    def _base_query(figure_queryset, year, skip_total_figures=False):
        qs = figure_queryset.annotate(
            year=models.Value(year, output_field=models.IntegerField()),
            cause_category=models.Case(
                models.When(figure_cause=Crisis.CRISIS_TYPE.CONFLICT, then=models.F('violence__name')),
                models.When(figure_cause=Crisis.CRISIS_TYPE.DISASTER, then=models.F('disaster_category__name')),
            ),
            cause_type=models.Case(
                models.When(figure_cause=Crisis.CRISIS_TYPE.CONFLICT, then=models.F('violence_sub_type__name')),
                models.When(figure_cause=Crisis.CRISIS_TYPE.DISASTER, then=models.F('disaster_type__name')),
            ),
            cause_subtype=models.Case(
                models.When(
                    figure_cause=Crisis.CRISIS_TYPE.DISASTER,
                    disaster_type__name='Storm',
                    disaster_sub_type__name__in=[
                        "Tornado",
                        "Typhoon/Hurricane/Cyclone",
                    ],
                    then=models.Value('Cyclone', output_field=models.CharField()),
                ),
                models.When(
                    figure_cause=Crisis.CRISIS_TYPE.DISASTER,
                    disaster_type__name='Storm',
                    then=models.Value('Other storms', output_field=models.CharField()),
                ),
            ),
        ).order_by().values(
            'country',
            'figure_cause',
            'category',
            'cause_category',
            'cause_type',
            'cause_subtype',
        ).annotate(
            **(
                {
                    'total_total_figures': models.Value(None, output_field=models.IntegerField()),
                } if skip_total_figures else {
                    'total_total_figures': models.Sum('total_figures'),
                }
            ),
        ).values(
            **{column: value for column, (value, _) in headers.items()}
        ).order_by(
            'country',
            'figure_cause',
            'category',
            'cause_category',
            'cause_type',
            'cause_subtype',
        )
        return qs

    def _year_run(year):
        year_int = int(year)
        start_date = datetime.datetime(year=year_int, month=1, day=1)
        end_date = datetime.datetime(year=year_int, month=12, day=31)

        hide_disaster_total_figures = False
        if 2016 <= year <= 2020:
            hide_disaster_total_figures = True

        figure_queryset = Figure.objects.filter(role=Figure.ROLE.RECOMMENDED)
        # Figures QS
        # -- Base
        nd_figure_qs = Figure.filtered_nd_figures(
            qs=figure_queryset,
            start_date=start_date,
            end_date=end_date
        )
        stock_figure_qs = Figure.filtered_idp_figures(
            qs=figure_queryset,
            start_date=start_date,
            end_date=end_date,
        )
        # Specific
        conflict_nd_figure_qs = nd_figure_qs.filter(event__event_type=Crisis.CRISIS_TYPE.CONFLICT)
        conflict_stock_figure_qs = stock_figure_qs.filter(event__event_type=Crisis.CRISIS_TYPE.CONFLICT)
        disaster_nd_figure_qs = nd_figure_qs.filter(event__event_type=Crisis.CRISIS_TYPE.DISASTER)
        disaster_stock_figure_qs = stock_figure_qs.filter(event__event_type=Crisis.CRISIS_TYPE.DISASTER)

        # QS
        conflict_nd_qs = _base_query(conflict_nd_figure_qs, year)
        conflict_stock_qs = _base_query(conflict_stock_figure_qs, year)
        disaster_nd_qs = _base_query(disaster_nd_figure_qs, year)
        disaster_stock_qs = _base_query(disaster_stock_figure_qs, year, skip_total_figures=hide_disaster_total_figures)
        # ALL QS
        qs = conflict_nd_qs.union(conflict_stock_qs, disaster_nd_qs, disaster_stock_qs)
        return qs

    countries_iso3_idmc_short_name_map = {
        iso3: title
        for iso3, title in Country.objects.values_list(
            'iso3',
            'idmc_short_name',
        )
    }

    def _run():
        start_year = 2016
        end_year = gidd_year
        existing_data_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'gidd_existing_data_tab_1.csv.gz',
        )
        for row in load_csv(existing_data_path, list(headers.keys()), gz=True):
            yield {
                **row,
                'Country': countries_iso3_idmc_short_name_map.get(
                    row['ISO3'],
                    row['Country'],  # Use raw text as fallback
                ),
            }

        for year in range(start_year, end_year + 1):
            for datum in _year_run(year):
                yield datum

    return (
        {
            column: renderer for column, (_, renderer) in headers.items()
        },
        _run(),
    )


def tab_2(gidd_year):
    headers = {
        'ISO3': (models.F('iso3s'), str_list_render),
        'Countries': (models.F('countries_name'), str_list_render),
        'Geographic Regions': (models.F('geographic_regions'), str_list_render),
        'year': (models.F('year'), noop),
        'Id': (models.F('id'), noop),
        'Event Name': (models.F('name'), noop),
        'ND Figure': (models.F(Event.ND_FIGURES_ANNOTATE), noop),
        'IDPs Figure': (models.F(Event.IDP_FIGURES_ANNOTATE), noop),
        'Start Date': (models.F('start_date'), noop),
        'End Date': (models.F('end_date'), noop),
        'Event Cause': (models.F('event_type'), cause_enum_list_render),
        'Disaster Category': (models.F('disaster_category__name'), noop),
        'Disaster Sub Category': (models.F('disaster_sub_category__name'), noop),
        'Disaster Type': (models.F('disaster_type__name'), noop),
        'Disaster Sub Type': (models.F('disaster_sub_type__name'), noop),
        'Violence': (models.F('violence__name'), noop),
        'Violence Sub Type Name': (models.F('violence_sub_type__name'), noop),
        'OSV Sub Type': (models.F('osv_sub_type__name'), noop),
        'Crisis Name': (models.F('crisis__name'), noop),
        'Crisis Id': (models.F('crisis__id'), noop),
    }

    # Using different reference time
    start_date = datetime.datetime(gidd_year, 1, 1)
    end_date = datetime.datetime(gidd_year, 12, 31)
    figures = Figure.objects.all()
    qs = Event.objects.annotate(
        **{
            Event.ND_FIGURES_ANNOTATE: models.Subquery(
                Figure.filtered_nd_figures(
                    figures.filter(
                        event=models.OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                    ),
                    start_date=start_date,
                    end_date=end_date,
                ).order_by().values('event').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
            Event.IDP_FIGURES_ANNOTATE: models.Subquery(
                Figure.filtered_idp_figures(
                    figures.filter(
                        event=models.OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                    ),
                    start_date=start_date,
                    end_date=end_date,
                ).order_by().values('event').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
        },
        iso3s=ArrayAgg('countries__iso3', distinct=True),
        countries_name=ArrayAgg('countries__idmc_short_name', distinct=True),
        geographic_regions=ArrayAgg(get_geographic_regions_query('countries'), distinct=True),
        year=Coalesce(
            ExtractYear('end_date'),
            ExtractYear('start_date'),
        ),
    ).exclude(
        **{
            Event.ND_FIGURES_ANNOTATE: 0,
            Event.IDP_FIGURES_ANNOTATE: 0,
        }
    ).order_by('year').values(**{column: value for column, (value, _) in headers.items()})

    return {column: renderer for column, (_, renderer) in headers.items()}, qs


def generate_xlsx(gidd_year: int):
    wb = Workbook()
    if wb.active:
        del wb[wb.active.title]
    for tab_name, generator in [
        ('Tab 1', tab_1),
        ('Tab 2', tab_2),
    ]:
        data = run_csv(generator, gidd_year)
        ws = wb.create_sheet(tab_name)
        for datum in data:
            ws.append(datum)
    return save_virtual_workbook(wb)
