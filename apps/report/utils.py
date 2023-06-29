from django.utils import timezone
from django.db.models.functions import Extract, Coalesce
from django.db import models
from django.db.models import (
    Sum,
    Count,
    Q,
    F,
    Subquery,
    OuterRef,
    Min,
    Max,
    Value,
)
from django.contrib.postgres.aggregates import StringAgg
from collections import OrderedDict
from datetime import timedelta
from apps.entry.models import Figure
from apps.crisis.models import Crisis
from apps.country.models import (
    CountryPopulation,
    Country,
    CountryRegion,
)
from utils.common import is_grid_or_myu_report
EXCEL_FORMULAE = {
    'per_100k': '=IF({key2}{{row}} <> "", (100000 * {key1}{{row}})/{key2}{{row}}, "")',
    'percent_variation': '=IF({key2}{{row}}, 100 * ({key1}{{row}} - {key2}{{row}})/{key2}{{row}}, "")',
}


def excel_column_key(headers, header) -> str:
    seed = ord('A')
    return chr(list(headers.keys()).index(header) + seed)


def report_global_numbers(report):
    conflict_filter = dict(
        role=Figure.ROLE.RECOMMENDED,
        event__event_type=Crisis.CRISIS_TYPE.CONFLICT,
    )
    disaster_filter = dict(
        role=Figure.ROLE.RECOMMENDED,
        event__event_type=Crisis.CRISIS_TYPE.DISASTER,
    )
    data = report.report_figures.aggregate(
        flow_disaster_total=Coalesce(
            Sum(
                'total_figures',
                filter=Q(
                    **disaster_filter,
                    category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                )
            ), 0
        ),
        flow_conflict_total=Coalesce(
            Sum(
                'total_figures',
                filter=Q(
                    **conflict_filter,
                    category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                )
            ), 0
        ),
        stock_conflict_total=Coalesce(
            Sum(
                'total_figures',
                filter=Q(
                    Q(
                        end_date__isnull=True,
                    ) | Q(
                        end_date__isnull=False,
                        end_date__gte=report.filter_figure_end_before or timezone.now().date(),
                    ),
                    **conflict_filter,
                    category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
                )
            ), 0
        ),
        event_disaster_count=Coalesce(
            Count(
                'event',
                filter=Q(
                    **disaster_filter,
                ),
                distinct=True
            ), 0
        ),
        conflict_countries_count=Coalesce(
            Count(
                'country',
                filter=Q(
                    **conflict_filter,
                ),
                distinct=True
            ), 0
        ),
        disaster_countries_count=Coalesce(
            Count(
                'country',
                filter=Q(
                    **disaster_filter,
                ),
                distinct=True
            ), 0
        ),
    )
    data['countries_count'] = data['conflict_countries_count'] + data['disaster_countries_count']
    data['flow_total'] = data['flow_disaster_total'] + data['flow_conflict_total']
    data['flow_conflict_percent'] = 100 * data['flow_conflict_total'] / data['flow_total'] if data['flow_total'] else 0
    data['flow_disaster_percent'] = 100 * data['flow_disaster_total'] / data['flow_total'] if data['flow_total'] else 0

    # this is simply for placeholder
    formatted_headers = {
        'one': '',
        'two': '',
        'three': '',
    }
    formatted_data = [
        dict(
            one='Conflict',
        ),
        dict(
            one='Data',
        ),
        dict(
            one=f'Sum of ND {report.name}',
            two=f'Sum of IDPs {report.name}',
        ),
        dict(
            one=data['flow_conflict_total'],
            two=data['stock_conflict_total'],
        ),
        dict(
            one='',
        ),
        dict(
            one='Disaster',
        ),
        dict(
            one='Data',
        ),
        dict(
            one=f'Sum of ND {report.name}',
            two=f'Number of Events of {report.name}',
        ),
        dict(
            one=data['flow_disaster_total'],
            two=data['event_disaster_count'],
        ),
        dict(
            one='',
        ),
        dict(
            one='Total Internal Displacements (Conflict + Disaster)',
            two=data['flow_total']
        ),
        dict(
            one='Conflict',
            two=f"{data['flow_conflict_percent']}%",
        ),
        dict(
            one='Disaster',
            two=f"{data['flow_disaster_percent']}%",
        ),
        dict(
            one='',
        ),
        dict(
            one='Number of countries with figures',
            two=data['countries_count']
        ),
        dict(
            one='Conflict',
            two=data['conflict_countries_count'],
        ),
        dict(
            one='Disaster',
            two=data['disaster_countries_count'],
        ),
    ]

    return dict(
        headers=formatted_headers,
        data=formatted_data,
        formulae=dict(),
    )


def report_stat_flow_country(report):
    headers = {
        'id': 'ID',
        'iso3': 'ISO3',
        'idmc_short_name': 'Country',
        'region__name': 'Region',
        Country.ND_CONFLICT_ANNOTATE: f'Conflict ND {report.name}',
        Country.ND_DISASTER_ANNOTATE: f'Disaster ND {report.name}',
        'total': f'Total ND {report.name}'
    }

    def get_key(header):
        return excel_column_key(headers, header)

    formulae = {}
    data = Country.objects.filter(
        id__in=report.report_figures.values('country')
    ).annotate(
        **Country._total_figure_disaggregation_subquery(
            report.report_figures,
            ignore_dates=True,
        )
    ).annotate(
        total=Coalesce(
            F(Country.ND_CONFLICT_ANNOTATE), 0
        ) + Coalesce(
            F(Country.ND_DISASTER_ANNOTATE), 0
        )
    ).order_by('id').values(
        *list(headers.keys())
    )
    return {
        'headers': headers,
        'data': data,
        'formulae': formulae,
    }


def report_stat_flow_region(report):
    headers = {
        'id': 'ID',
        'name': 'Region',
        CountryRegion.ND_CONFLICT_ANNOTATE: f'Conflict ND {report.name}',
        CountryRegion.ND_DISASTER_ANNOTATE: f'Disaster ND {report.name}',
        'total': f'Total ND {report.name}',
    }

    # NOTE: {{ }} turns into { } after the first .format
    formulae = {}
    data = CountryRegion.objects.filter(
        id__in=report.report_figures.values('country__region')
    ).annotate(
        **CountryRegion._total_figure_disaggregation_subquery(
            report.report_figures,
            ignore_dates=True,
        )
    ).annotate(
        total=Coalesce(
            F(CountryRegion.ND_CONFLICT_ANNOTATE), 0
        ) + Coalesce(
            F(CountryRegion.ND_DISASTER_ANNOTATE), 0
        )
    ).values(
        *list(headers.keys())
    )
    return {
        'headers': headers,
        'data': data,
        'formulae': formulae,
    }


def report_stat_conflict_country(report, include_history):
    headers = OrderedDict(dict(
        iso3='ISO3',
        name='Country',
        country_population='Population',
        flow_total=f'ND {report.name}',
        stock_total=f'IDPs {report.name}',
        flow_total_last_year='ND last year',
        stock_total_last_year='IDPs last year',
        flow_historical_average='ND historical average',
        stock_historical_average='IDPs historical average',
        # provisional and returns
        # historical average for flow an stock NOTE: coming from different db
    ))

    def get_key(header):
        return excel_column_key(headers, header)

    # NOTE: {{ }} turns into { } after the first .format
    formulae = {
        'ND per 100k population': EXCEL_FORMULAE['per_100k'].format(
            key1=get_key('flow_total'), key2=get_key('country_population')
        ),
        'ND percent variation wrt last year':
            EXCEL_FORMULAE['percent_variation'].format(
            key1=get_key('flow_total'), key2=get_key('flow_total_last_year')
        ),
        'ND percent variation wrt average':
            EXCEL_FORMULAE['percent_variation'].format(
            key1=get_key('flow_total'), key2=get_key('flow_historical_average')
        ),
        'IDPs per 100k population': EXCEL_FORMULAE['per_100k'].format(
            key1=get_key('stock_total'), key2=get_key('country_population')
        ),
        'IDPs percent variation wrt last year':
            EXCEL_FORMULAE['percent_variation'].format(
            key1=get_key('stock_total'), key2=get_key('stock_total_last_year')
        ),
        'IDPs percent variation wrt average':
            EXCEL_FORMULAE['percent_variation'].format(
            key1=get_key('stock_total'), key2=get_key('stock_historical_average')
        ),
    }
    global_filter = dict(
        role=Figure.ROLE.RECOMMENDED,
        event__event_type=Crisis.CRISIS_TYPE.CONFLICT
    )

    data = report.report_figures.values('country').order_by().annotate(
        country_population=Subquery(
            CountryPopulation.objects.filter(
                year=int(report.filter_figure_start_after.year),
                country=OuterRef('country'),
            ).values('population')
        ),
        iso3=F('country__iso3'),
        name=F('country__idmc_short_name'),
        flow_total=Sum('total_figures', filter=Q(
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            **global_filter
        )),
        stock_total=Sum('total_figures', filter=Q(
            Q(
                end_date__isnull=True,
            ) | Q(
                end_date__isnull=False,
                end_date__gte=report.filter_figure_end_before or timezone.now().date(),
            ),
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            **global_filter
        )),
    )

    if is_grid_or_myu_report(report.filter_figure_start_after, report.filter_figure_end_before) and include_history:
        data = data.annotate(
            flow_total_last_year=Subquery(
                Figure.objects.filter(
                    start_date__gte=report.filter_figure_start_after - timedelta(days=365),
                    end_date__lte=report.filter_figure_end_before - timedelta(days=365),
                    country=OuterRef('country'),
                    category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                    **global_filter
                ).annotate(
                    _total=Sum('total_figures')
                ).values('_total').annotate(total=F('_total')).values('total')
            ),
            flow_historical_average=Subquery(
                Figure.objects.filter(
                    start_date__lt=report.filter_figure_start_after,
                    # only consider the figures in the given month range
                    start_date__month__gte=report.filter_figure_start_after.month,
                    end_date__month__lte=report.filter_figure_end_before.month,
                    country=OuterRef('country'),
                    category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                    **global_filter
                ).annotate(
                    min_year=Min(Extract('start_date', 'year')),
                    max_year=Max(Extract('start_date', 'year')),
                ).annotate(
                    _total=Sum('total_figures') / (F('max_year') - F('min_year') + 1)
                ).values('_total').annotate(total=F('_total')).values('total')
            ),
            stock_total_last_year=Subquery(
                Figure.objects.filter(
                    start_date__lte=report.filter_figure_end_before - timedelta(days=365),
                    country=OuterRef('country'),
                    category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
                    **global_filter
                ).filter(
                    Q(
                        end_date__isnull=False,
                        end_date__gte=report.filter_figure_end_before - timedelta(days=365)
                    ) | Q(
                        end_date__isnull=True
                    ),
                ).annotate(
                    _total=Sum('total_figures')
                ).values('_total').annotate(total=F('_total')).values('total')
            ),
            # TODO: we will need to handle each year separately for idp figures to get the average
            stock_historical_average=Value('...', output_field=models.CharField()),
        )
    return {
        'headers': headers,
        'data': data,
        'formulae': formulae,
        'aggregation': None,
    }


def report_stat_conflict_region(report, include_history):
    headers = OrderedDict(dict(
        name='Region',
        region_population='Population',
        flow_total=f'ND {report.name}',
        stock_total=f'IDPs {report.name}',
        flow_total_last_year='ND Last Year',
        stock_total_last_year='IDPs Last Year',
        flow_historical_average='ND Historical Average',
        stock_historical_average='IDPs Historical Average',
        # provisional and returns
    ))

    def get_key(header):
        return excel_column_key(headers, header)

    # NOTE: {{ }} turns into { } after the first .format
    formulae = OrderedDict({
        'ND per 100k population': EXCEL_FORMULAE['per_100k'].format(
            key1=get_key('flow_total'), key2=get_key('region_population')
        ),
        'ND percent variation wrt last year':
            EXCEL_FORMULAE['percent_variation'].format(
            key1=get_key('flow_total'), key2=get_key('flow_total_last_year')
        ),
        'ND percent variation wrt average':
            EXCEL_FORMULAE['percent_variation'].format(
            key1=get_key('flow_total'), key2=get_key('flow_historical_average')
        ),
        'IDPs per 100k population': EXCEL_FORMULAE['per_100k'].format(
            key1=get_key('stock_total'), key2=get_key('region_population')
        ),
        'IDPs percent variation wrt last year':
            EXCEL_FORMULAE['percent_variation'].format(
            key1=get_key('stock_total'), key2=get_key('stock_total_last_year')
        ),
        'IDPs percent variation wrt average':
            EXCEL_FORMULAE['percent_variation'].format(
            key1=get_key('stock_total'), key2=get_key('stock_historical_average')
        ),
    })
    global_filter = dict(
        role=Figure.ROLE.RECOMMENDED,
        event__event_type=Crisis.CRISIS_TYPE.CONFLICT
    )

    data = report.report_figures.annotate(
        region=F('country__region')
    ).values('region').order_by().annotate(
        region_population=Subquery(
            CountryPopulation.objects.filter(
                year=int(report.filter_figure_start_after.year),
                country__region=OuterRef('region'),
            ).annotate(
                total_population=Sum('population'),
            ).values('total_population')[:1]
        ),
        name=F('country__region__name'),
        flow_total=Sum('total_figures', filter=Q(
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            **global_filter
        )),
        stock_total=Sum('total_figures', filter=Q(
            Q(
                end_date__isnull=True,
            ) | Q(
                end_date__isnull=False,
                end_date__gte=report.filter_figure_end_before or timezone.now().date(),
            ),
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            **global_filter,
        )),
    )

    if is_grid_or_myu_report(report.filter_figure_start_after, report.filter_figure_end_before) and include_history:
        data = data.annotate(
            flow_total_last_year=Subquery(
                Figure.objects.filter(
                    start_date__gte=report.filter_figure_start_after - timedelta(days=365),
                    end_date__lte=report.filter_figure_end_before - timedelta(days=365),
                    country__region=OuterRef('region'),
                    category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                    **global_filter
                ).annotate(
                    _total=Sum('total_figures')
                ).values('_total').annotate(total=F('_total')).values('total')
            ),
            flow_historical_average=Subquery(
                Figure.objects.filter(
                    start_date__lt=report.filter_figure_start_after,
                    # only consider the figures in the given month range
                    start_date__month__gte=report.filter_figure_start_after.month,
                    country__region=OuterRef('region'),
                    category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                    **global_filter
                ).annotate(
                    min_year=Min(Extract('start_date', 'year')),
                    max_year=Max(Extract('start_date', 'year')),
                ).annotate(
                    _total=Sum('total_figures') / (F('max_year') - F('min_year') + 1)
                ).values('_total').annotate(total=F('_total')).values('total')
            ),
            stock_total_last_year=Subquery(
                Figure.objects.filter(
                    start_date__lte=report.filter_figure_end_before - timedelta(days=365),
                    country__region=OuterRef('region'),
                    category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
                    **global_filter
                ).filter(
                    Q(
                        end_date__isnull=False,
                        end_date__gte=report.filter_figure_end_before - timedelta(days=365)
                    ) | Q(
                        end_date__isnull=True
                    ),
                ).annotate(
                    _total=Sum('total_figures')
                ).values('_total').annotate(total=F('_total')).values('total')
            ),
            # TODO: stock historical average must be pre-calculated for each year
            stock_historical_average=Value('...', output_field=models.CharField()),
        )
    return {
        'headers': headers,
        'data': data,
        'formulae': formulae,
        'aggregation': None,
    }


def report_stat_conflict_typology(report):
    headers = OrderedDict(dict(
        iso3='ISO3',
        name='IDMC short name',
        typology='Conflict typology',
        total='Figure',
    ))
    filtered_report_figures = report.report_figures.filter(
        role=Figure.ROLE.RECOMMENDED,
        event__event_type=Crisis.CRISIS_TYPE.CONFLICT,
        category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
    ).values('country').order_by()

    data = filtered_report_figures.filter(disaggregation_conflict__gt=0).annotate(
        name=F('country__idmc_short_name'),
        iso3=F('country__iso3'),
        total=Sum('disaggregation_conflict', filter=Q(disaggregation_conflict__gt=0)),
        typology=models.Value('Armed Conflict', output_field=models.CharField())
    ).values('name', 'iso3', 'total', 'typology').union(
        filtered_report_figures.filter(disaggregation_conflict_political__gt=0).annotate(
            name=F('country__idmc_short_name'),
            iso3=F('country__iso3'),
            total=Sum(
                'disaggregation_conflict_political',
                filter=Q(disaggregation_conflict_political__gt=0)
            ),
            typology=models.Value('Violence - Political', output_field=models.CharField())
        ).values('name', 'iso3', 'total', 'typology'),
        filtered_report_figures.filter(disaggregation_conflict_criminal__gt=0).annotate(
            name=F('country__idmc_short_name'),
            iso3=F('country__iso3'),
            total=Sum(
                'disaggregation_conflict_criminal',
                filter=Q(disaggregation_conflict_criminal__gt=0)
            ),
            typology=models.Value('Violence - Criminal', output_field=models.CharField())
        ).values('name', 'iso3', 'total', 'typology'),
        filtered_report_figures.filter(disaggregation_conflict_communal__gt=0).annotate(
            name=F('country__idmc_short_name'),
            iso3=F('country__iso3'),
            total=Sum(
                'disaggregation_conflict_communal',
                filter=Q(disaggregation_conflict_communal__gt=0)
            ),
            typology=models.Value('Violence - Communal', output_field=models.CharField())
        ).values('name', 'iso3', 'total', 'typology'),
        filtered_report_figures.filter(disaggregation_conflict_other__gt=0).annotate(
            name=F('country__idmc_short_name'),
            iso3=F('country__iso3'),
            total=Sum(
                'disaggregation_conflict_other',
                filter=Q(disaggregation_conflict_other__gt=0)
            ),
            typology=models.Value('Other', output_field=models.CharField())
        ).values('name', 'iso3', 'total', 'typology')
    ).values('name', 'iso3', 'typology', 'total').order_by('typology')

    # further aggregation
    aggregation_headers = OrderedDict(dict(
        typology='Conflict typology',
        total='Sum of figure',
    ))
    aggregation_formula = dict()

    filtered_report_figures = report.report_figures.filter(
        role=Figure.ROLE.RECOMMENDED,
        event__event_type=Crisis.CRISIS_TYPE.CONFLICT,
        category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
    )

    aggregation_data = filtered_report_figures.aggregate(
        total_conflict=Sum('disaggregation_conflict'),
        total_conflict_political=Sum('disaggregation_conflict_political'),
        total_conflict_other=Sum('disaggregation_conflict_other'),
        total_conflict_criminal=Sum('disaggregation_conflict_criminal'),
        total_conflict_communal=Sum('disaggregation_conflict_communal'),
    )
    aggregation_data = [
        dict(
            typology='Armed Conflict',
            total=aggregation_data['total_conflict'],
        ),
        dict(
            typology='Violence - Political',
            total=aggregation_data['total_conflict_political'],
        ),
        dict(
            typology='Violence - Criminal',
            total=aggregation_data['total_conflict_criminal'],
        ),
        dict(
            typology='Violence - Communal',
            total=aggregation_data['total_conflict_communal'],
        ),
        dict(
            typology='Other',
            total=aggregation_data['total_conflict_other'],
        ),
    ]

    return {
        'headers': headers,
        'data': data,
        'formulae': dict(),
        'aggregation': dict(
            headers=aggregation_headers,
            formulae=aggregation_formula,
            data=aggregation_data,
        )
    }


def report_disaster_event(report):
    headers = OrderedDict(dict(
        event_id='Event ID',
        event_name='Event name',
        event_year='Event year',
        event_start_date='Start date',
        event_end_date='End date',
        event_category='Hazard category',
        event_sub_category='Hazard sub category',
        dtype='Hazard type',
        dsub_type='Hazard sub type',
        affected_iso3='Affected ISO3',
        affected_names='Affected countries',
        affected_countries='Number of affected countries',
        flow_total='ND' + report.name,
    ))

    def get_key(header):
        return excel_column_key(headers, header)

    # NOTE: {{ }} turns into { } after the first .format
    global_filter = dict(
        role=Figure.ROLE.RECOMMENDED,
        event__event_type=Crisis.CRISIS_TYPE.DISASTER
    )

    data = report.report_figures.filter(
        **global_filter
    ).values('event').order_by().annotate(
        event_id=F('event_id'),
        event_name=F('event__name'),
        event_year=Extract('event__end_date', 'year'),
        event_start_date=F('event__start_date'),
        event_end_date=F('event__end_date'),
        event_category=F('event__disaster_category__name'),
        event_sub_category=F('event__disaster_sub_category__name'),
        dtype=F('event__disaster_type__name'),
        dsub_type=F('event__disaster_sub_type__name'),
        flow_total=Sum('total_figures', filter=Q(category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT)),
        affected_countries=Count('country', distinct=True),
        affected_iso3=StringAgg('country__iso3', '; ', distinct=True),
        affected_names=StringAgg('country__idmc_short_name', ';  ', distinct=True),
    )
    return {
        'headers': headers,
        'data': data,
        'formulae': dict(),
    }


def report_disaster_country(report, include_history):
    headers = OrderedDict(dict(
        country_iso3='ISO3',
        country_name='Name',
        country_region='Region',
        events_count='Events count',
        country_population='Country population',
        flow_total=f'ND {report.name}',
        flow_total_last_year='ND last year',
        flow_historical_average='ND historical average',
    ))

    def get_key(header):
        return excel_column_key(headers, header)

    formulae = {
        'ND per 100k population': EXCEL_FORMULAE['per_100k'].format(
            key1=get_key('flow_total'), key2=get_key('country_population')
        ),
        'ND percent variation wrt last year':
            EXCEL_FORMULAE['percent_variation'].format(
            key1=get_key('flow_total'), key2=get_key('flow_total_last_year')
        ),
        'ND percent variation wrt average':
            EXCEL_FORMULAE['percent_variation'].format(
            key1=get_key('flow_total'), key2=get_key('flow_historical_average')
        ),
    }
    global_filter = dict(
        role=Figure.ROLE.RECOMMENDED,
        event__event_type=Crisis.CRISIS_TYPE.DISASTER,
    )
    data = report.report_figures.filter(
        **global_filter
    ).values('country').order_by().annotate(
        country_iso3=F('country__iso3'),
        country_name=F('country__idmc_short_name'),
        country_region=F('country__region__name'),
        events_count=Count('event', distinct=True),
        country_population=Subquery(
            CountryPopulation.objects.filter(
                year=int(report.filter_figure_start_after.year),
                country=OuterRef('country'),
            ).values('population')
        ),
        flow_total=Sum('total_figures', filter=Q(
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            **global_filter
        )),
    )

    if is_grid_or_myu_report(report.filter_figure_start_after, report.filter_figure_end_before) and include_history:
        data = data.annotate(
            flow_total_last_year=Subquery(
                Figure.objects.filter(
                    start_date__gte=report.filter_figure_start_after - timedelta(days=365),
                    end_date__lte=report.filter_figure_end_before - timedelta(days=365),
                    country=OuterRef('country'),
                    category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                    **global_filter
                ).annotate(
                    _total=Sum('total_figures')
                ).values('_total').annotate(total=F('_total')).values('total')
            ),
            flow_historical_average=Subquery(
                Figure.objects.filter(
                    start_date__lt=report.filter_figure_start_after,
                    # only consider the figures in the given month range
                    start_date__month__gte=report.filter_figure_start_after.month,
                    end_date__month__lte=report.filter_figure_end_before.month,
                    country=OuterRef('country'),
                    category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                    **global_filter
                ).annotate(
                    min_year=Min(Extract('start_date', 'year')),
                    max_year=Max(Extract('start_date', 'year')),
                ).annotate(
                    _total=Sum('total_figures') / (F('max_year') - F('min_year') + 1)
                ).values('_total').annotate(total=F('_total')).values('total')
            ),
        )

    return {
        'headers': headers,
        'data': data,
        'formulae': formulae,
        'aggregation': None,
    }


def report_disaster_region(report, include_history):
    headers = OrderedDict(dict(
        region_name='Region',
        events_count='Events count',
        region_population='Region population',
        flow_total=f'ND {report.name}',
        flow_total_last_year='ND last year',
        flow_historical_average='ND historical average',
    ))

    def get_key(header):
        return excel_column_key(headers, header)

    formulae = {
        'ND per 100k population': EXCEL_FORMULAE['per_100k'].format(
            key1=get_key('flow_total'), key2=get_key('region_population')
        ),
        'ND percent variation wrt last year':
            EXCEL_FORMULAE['percent_variation'].format(
            key1=get_key('flow_total'), key2=get_key('flow_total_last_year')
        ),
        'ND percent variation wrt average':
            EXCEL_FORMULAE['percent_variation'].format(
            key1=get_key('flow_total'), key2=get_key('flow_historical_average')
        ),
    }
    global_filter = dict(
        role=Figure.ROLE.RECOMMENDED,
        event__event_type=Crisis.CRISIS_TYPE.DISASTER,
    )
    data = report.report_figures.filter(
        **global_filter
    ).annotate(
        region=F('country__region')
    ).values('country__region').order_by().annotate(
        region_name=F('country__region__name'),
        country_region=F('country__region__name'),
        events_count=Count('event', distinct=True),
        region_population=Subquery(
            CountryPopulation.objects.filter(
                country__region=OuterRef('region'),
                year=int(report.filter_figure_start_after.year),
            ).annotate(
                total_population=Sum('population')
            ).values('total_population')[:1]
        ),
        flow_total=Sum('total_figures', filter=Q(
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            **global_filter
        )),
    )

    if is_grid_or_myu_report(report.filter_figure_start_after, report.filter_figure_end_before) and include_history:
        data = data.annotate(
            flow_total_last_year=Subquery(
                Figure.objects.filter(
                    start_date__gte=report.filter_figure_start_after - timedelta(days=365),
                    end_date__lte=report.filter_figure_end_before - timedelta(days=365),
                    country__region=OuterRef('country__region'),
                    category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                    **global_filter
                ).annotate(
                    _total=Sum('total_figures')
                ).values('_total').annotate(total=F('_total')).values('total')
            ),
            flow_historical_average=Subquery(
                Figure.objects.filter(
                    start_date__lt=report.filter_figure_start_after,
                    # only consider the figures in the given month range
                    start_date__month__gte=report.filter_figure_start_after.month,
                    end_date__month__lte=report.filter_figure_end_before.month,
                    country__region=OuterRef('country__region'),
                    category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                    **global_filter
                ).annotate(
                    min_year=Min(Extract('start_date', 'year')),
                    max_year=Max(Extract('start_date', 'year')),
                ).annotate(
                    _total=Sum('total_figures') / (F('max_year') - F('min_year') + 1)
                ).values('_total').annotate(total=F('_total')).values('total')
            ),
        )

    return {
        'headers': headers,
        'data': data,
        'formulae': formulae,
    }


def report_get_excel_sheets_data(report, include_history=False):
    '''
    Returns title and corresponding computed property
    '''
    return {
        'Global Numbers': report_global_numbers(report),
        'ND Country': report_stat_flow_country(report),
        'ND Region': report_stat_flow_region(report),
        'Conflict Country': report_stat_conflict_country(report, include_history),
        'Conflict Region': report_stat_conflict_region(report, include_history),
        'Conflict Typology': report_stat_conflict_typology(report),
        'Disaster Event': report_disaster_event(report),
        'Disaster Country': report_disaster_country(report, include_history),
        'Disaster Region': report_disaster_region(report, include_history)
    }
