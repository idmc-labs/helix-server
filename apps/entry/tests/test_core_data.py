import typing
from datetime import date, timedelta
from random import randint
from math import sqrt

from django.conf import settings
from django.test import override_settings

from utils.factories import (
    EventFactory,
    CrisisFactory,
    CountryFactory,
    FigureFactory,
    EntryFactory,
    ReportFactory,
)
from apps.crisis.models import Crisis
from apps.event.models import Event
from apps.entry.models import Figure, Entry
from apps.report.models import Report
from apps.country.models import Country
from apps.users.enums import USER_ROLE
from utils.tests import (
    HelixGraphQLTestCase,
    create_user_with_role,
)


def get_figure_value_sum(figures: typing.List[int]):
    '''If the list is empty or None, sum should be None'''
    if figures:
        return sum(figures)


def get_figure_aggregations(figures: typing.List[Figure]):
    return {
        'disaster_idps': get_figure_value_sum([
            figure.total_figures for figure in figures
            if (
                figure.event.event_type == Crisis.CRISIS_TYPE.DISASTER and
                figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
                figure.role == Figure.ROLE.RECOMMENDED
            )
        ]),
        'disaster_nds': get_figure_value_sum([
            figure.total_figures for figure in figures
            if (
                figure.event.event_type == Crisis.CRISIS_TYPE.DISASTER and
                figure.category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT and
                figure.role == Figure.ROLE.RECOMMENDED
            )
        ]),
        'conflict_idps': get_figure_value_sum([
            figure.total_figures for figure in figures
            if (
                figure.event.event_type == Crisis.CRISIS_TYPE.CONFLICT and
                figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
                figure.role == Figure.ROLE.RECOMMENDED
            )
        ]),
        'conflict_nds': get_figure_value_sum([
            figure.total_figures for figure in figures
            if (
                figure.event.event_type == Crisis.CRISIS_TYPE.CONFLICT and
                figure.category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT and
                figure.role == Figure.ROLE.RECOMMENDED
            )
        ])
    }


def check_same_date(
    foo_date: date,
    bar_date: date,
) -> bool:
    return foo_date == bar_date


def check_date_inside_date_range(
    foo_date: date,
    start_date_range: date,
    end_date_range: date,
) -> bool:
    return start_date_range <= foo_date <= end_date_range


def check_date_range_inside_date_range(
    start_date: date,
    end_date: date,
    start_date_range: date,
    end_date_range: date,
) -> bool:
    if start_date.year != end_date.year:
        return start_date_range <= end_date <= end_date_range
    return start_date_range <= start_date <= end_date_range


def is_prime(n: int) -> bool:
    if (n <= 1):
        return False
    if (n == 2):
        return True
    # Check for even numbers
    if (n % 2 == 0):
        return False

    i = 3
    while i <= sqrt(n):
        if n % i == 0:
            return False
        i = i + 2

    return True


def prime_generator() -> typing.Iterator[int]:
    '''We are starting the prime number with 3'''
    n = 2
    while True:
        n += 1
        if is_prime(n):
            yield n


figure_value_generator = prime_generator()


class GetDatesDateRangeType(typing.TypedDict):
    start_date: date
    end_date: date


GetDatesTypes = typing.Literal[
    'single_year_touching_start',
    'single_year_touching_end',
    'single_year_not_touching',
    'point_touching_start',
    'point_touching_end',
    'point_not_touching',
    'multiple_year_without_gaps',
    'multiple_year_with_gaps',
]


def get_dates(_type: GetDatesTypes, year: int) -> GetDatesDateRangeType:
    start_of_year = date(year, 1, 1)
    end_of_year = date(year, 12, 31)
    if _type == 'single_year_touching_start':
        return {
            'start_date': start_of_year,
            'end_date': start_of_year + timedelta(days=randint(1, 100)),
        }
    if _type == 'single_year_touching_end':
        return {
            'start_date': end_of_year - timedelta(days=randint(1, 100)),
            'end_date': end_of_year,
        }
    if _type == 'single_year_not_touching':
        # NOTE: start day should be greater than end day
        return {
            'start_date': start_of_year + timedelta(days=randint(100, 150)),
            'end_date': start_of_year + timedelta(days=randint(151, 200)),
        }
    if _type == 'point_touching_start':
        return {
            'start_date': start_of_year,
            'end_date': start_of_year,
        }
    if _type == 'point_touching_end':
        return {
            'start_date': end_of_year,
            'end_date': end_of_year,
        }
    if _type == 'point_not_touching':
        # NOTE: both days should be same
        day = start_of_year + timedelta(days=randint(100, 200))
        return {
            'start_date': day,
            'end_date': day,
        }
    if _type == 'multiple_year_without_gaps':
        return {
            'start_date': end_of_year,
            'end_date': end_of_year + timedelta(days=1),
        }
    if _type == 'multiple_year_with_gaps':
        return {
            'start_date': end_of_year - timedelta(days=randint(1, 200)),
            'end_date': end_of_year + timedelta(days=(1 + randint(1, 200))),
        }
    raise Exception(f'Unknown type: {_type}')


@override_settings(
    GRAPHENE_DJANGO_EXTRAS={
        **settings.GRAPHENE_DJANGO_EXTRAS,
        'MAX_PAGE_SIZE': 999999,
    }
)
class TestCoreData(HelixGraphQLTestCase):
    @classmethod
    def init_data(cls):
        # Start from scratch
        # TODO: Find out why we have initial data before this.
        Country.objects.all().delete()
        Crisis.objects.all().delete()
        Event.objects.all().delete()
        Entry.objects.all().delete()
        Figure.objects.all().delete()
        Report.objects.all().delete()

        cls.start_year = start_year = 2010
        cls.end_year = end_year = 2013

        # Country
        cls.country_npl = country_npl = CountryFactory.create(iso3='NPL', name="Nepal")
        cls.country_ind = country_ind = CountryFactory.create(iso3='IND', name="India")
        cls.countries = countries = [country_npl, country_ind]

        # Crisis
        crises_1 = CrisisFactory.create(
            name='Crises-1',
            crisis_type=Crisis.CRISIS_TYPE.DISASTER,
        )
        crises_1.countries.add(*countries)
        crises_2 = CrisisFactory.create(
            name='Crises-2',
            crisis_type=Crisis.CRISIS_TYPE.CONFLICT,
        )
        crises_2.countries.add(*countries)
        crises_3 = CrisisFactory.create(
            name='Crises-3',
            crisis_type=Crisis.CRISIS_TYPE.CONFLICT,
        )
        crises_3.countries.add(country_npl)
        crises_4 = CrisisFactory.create(
            name='Crises-4',
            crisis_type=Crisis.CRISIS_TYPE.OTHER,
        )
        crises_4.countries.add(*countries)
        cls.crises = [crises_1, crises_2, crises_3, crises_4]

        # Entry
        # NOTE: For now we are re-using the entry for all figures
        entry = EntryFactory.create()

        # Events
        event_1 = EventFactory.create(
            name='Event-1',
            crisis=crises_1,
            event_type=crises_1.crisis_type,
            countries=[country_npl],
            actor=None,
        )
        event_2 = EventFactory.create(
            name='Event-2',
            crisis=crises_1,
            event_type=crises_1.crisis_type,
            countries=[country_ind],
            actor=None,
        )
        event_3 = EventFactory.create(
            name='Event-3',
            crisis=crises_2,
            event_type=crises_2.crisis_type,
            countries=[country_ind],
            actor=None,
        )
        event_4 = EventFactory.create(
            name='Event-4',
            crisis=crises_2,
            event_type=crises_2.crisis_type,
            countries=[country_npl],
            actor=None,
        )
        event_5 = EventFactory.create(
            name='Event-5',
            crisis=crises_2,
            event_type=crises_2.crisis_type,
            countries=countries,
            actor=None,
        )
        event_6 = EventFactory.create(
            name='Event-6',
            crisis=crises_3,
            event_type=crises_3.crisis_type,
            countries=[country_npl],
            actor=None,
        )
        event_7 = EventFactory.create(
            name='Event-7',
            crisis=crises_4,
            event_type=crises_4.crisis_type,
            countries=countries,
            actor=None,
        )
        cls.events = events = [event_1, event_2, event_3, event_4, event_5, event_6, event_7]

        # Reports
        cls.reports: list[Report] = []
        report_data_set: typing.List[typing.Tuple[int, typing.Union[None, Country]]] = [
            (year, country)
            for year in range(start_year, end_year + 1)
            for country in [None, *countries]
        ]
        for year, country in report_data_set:
            report_name = (
                f'GRID {year + 1}' if country is None else
                f'GRID {year + 1} - {country.iso3}'
            )
            report_start_date = date(year=year, month=1, day=1)
            report_end_date = date(year=year, month=12, day=31)
            report = ReportFactory.create(
                name=report_name,
                filter_figure_start_after=report_start_date,
                filter_figure_end_before=report_end_date,
                is_public=True,
            )
            if country:
                report.filter_figure_countries.set([country])
            cls.reports.append(report)

        figure_data_set: typing.List[typing.Tuple[int, Figure.ROLE, Country, Event]] = [
            (year, role, country, event)
            for year in range(start_year, end_year + 1)
            for role in [Figure.ROLE.RECOMMENDED, Figure.ROLE.TRIANGULATION]
            for event in events
            for country in event.countries.all()
        ]

        # Figures
        figures = []
        for year, role, country, event in figure_data_set:
            FIGURE_DATA_GENERATION_SET: typing.List[
                typing.Tuple[
                    Figure.FIGURE_CATEGORY_TYPES,
                    GetDatesTypes,
                ]
            ]
            # NOTE: For the last year, we do not want to have Dec 31
            # on the dataset so that we can check the aggreagtion for event and crisis
            if year == end_year:
                FIGURE_DATA_GENERATION_SET = [
                    # Internal Displacement
                    (Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT, 'single_year_not_touching'),
                    # IDPs
                    (Figure.FIGURE_CATEGORY_TYPES.IDPS, 'single_year_not_touching'),
                    # Others
                    (Figure.FIGURE_CATEGORY_TYPES.PARTIAL_STOCK, 'single_year_not_touching'),
                    (Figure.FIGURE_CATEGORY_TYPES.PARTIAL_FLOW, 'single_year_not_touching'),
                ]
            else:
                FIGURE_DATA_GENERATION_SET = [
                    # Internal Displacement
                    (Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT, 'single_year_touching_start'),
                    (Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT, 'single_year_not_touching'),
                    (Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT, 'single_year_touching_end'),
                    (Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT, 'point_touching_start'),
                    (Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT, 'point_not_touching'),
                    (Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT, 'point_touching_end'),
                    (Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT, 'multiple_year_with_gaps'),
                    (Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT, 'multiple_year_without_gaps'),
                    # IDPs
                    (Figure.FIGURE_CATEGORY_TYPES.IDPS, 'single_year_touching_start'),
                    (Figure.FIGURE_CATEGORY_TYPES.IDPS, 'single_year_not_touching'),
                    (Figure.FIGURE_CATEGORY_TYPES.IDPS, 'single_year_touching_end'),
                    # Others
                    (Figure.FIGURE_CATEGORY_TYPES.PARTIAL_STOCK, 'single_year_touching_start'),
                    (Figure.FIGURE_CATEGORY_TYPES.PARTIAL_STOCK, 'single_year_not_touching'),
                    (Figure.FIGURE_CATEGORY_TYPES.PARTIAL_STOCK, 'single_year_touching_end'),
                    (Figure.FIGURE_CATEGORY_TYPES.PARTIAL_FLOW, 'single_year_touching_start'),
                    (Figure.FIGURE_CATEGORY_TYPES.PARTIAL_FLOW, 'single_year_not_touching'),
                    (Figure.FIGURE_CATEGORY_TYPES.PARTIAL_FLOW, 'single_year_touching_end'),
                ]

            # Start creating figures
            for figure_category, get_date_type in FIGURE_DATA_GENERATION_SET:
                figure_kwargs = dict(
                    event=event,
                    entry=entry,
                    country=country,
                    role=role,
                    category=figure_category,
                    **get_dates(get_date_type, year),
                )
                # NOTE: We need to add iterations so that we have at least 2 values for aggregation on the same date
                figures.extend([
                    FigureFactory.build(**figure_kwargs, total_figures=next(figure_value_generator)),
                    FigureFactory.build(**figure_kwargs, total_figures=next(figure_value_generator))
                ])

        # Create in bulk
        Figure.objects.bulk_create(figures)
        cls.figures = list(Figure.objects.all().select_related('event'))

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.init_data()

    def setUp(self) -> None:
        super().setUp()
        self.user_monitoring_expert = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT.name,
            country=self.country_npl.id,
        )
        self.force_login(self.user_monitoring_expert)

    def test_figure_aggregation_in_countries(self):
        ''' Check for different years for each country '''
        for year in range(self.start_year, self.end_year + 1):
            country_aggregates = []
            for country in self.countries:
                filtered_figures = []
                for figure in self.figures:
                    if (
                        figure.country == country and
                        figure.category in Figure.flow_list() and
                        check_date_range_inside_date_range(
                            figure.start_date,
                            figure.end_date,
                            date(year, 1, 1),
                            date(year, 12, 31),
                        )
                    ):
                        filtered_figures.append(figure)
                    elif (
                        figure.country == country and
                        figure.category in Figure.stock_list() and
                        check_same_date(figure.end_date, date(year, 12, 31))
                    ):
                        filtered_figures.append(figure)

                country_aggregates.append({
                    'iso3': country.iso3,
                    **get_figure_aggregations(filtered_figures),
                })

            query = '''
                query MyQuery($year: Float!) {
                  countryList(
                      ordering: "id",
                      filters: {aggregateFigures: {year: $year}}
                  ) {
                    results {
                      id
                      name
                      iso3
                      totalStockDisaster
                      totalFlowDisaster
                      totalStockConflict
                      totalFlowConflict
                    }
                  }
                }
            '''
            r_data = self.query(query, variables={'year': year}).json()['data']['countryList']['results']
            system_data = [
                {
                    'iso3': i['iso3'],
                    'disaster_idps': i['totalStockDisaster'],
                    'disaster_nds': i['totalFlowDisaster'],
                    'conflict_idps': i['totalStockConflict'],
                    'conflict_nds': i['totalFlowConflict'],
                }
                for i in r_data
            ]
            assert country_aggregates == system_data

    def test_figure_aggregation_in_events(self):
        event_aggregates = []
        for event in self.events:
            max_date = max([
                figure.end_date for figure in self.figures
                if (
                    figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
                    figure.event == event and
                    figure.role == Figure.ROLE.RECOMMENDED
                )
            ])
            filtered_figures = []
            for figure in self.figures:
                if (
                    figure.event == event and
                    figure.category in Figure.flow_list()
                ):
                    filtered_figures.append(figure)
                elif (
                    figure.event == event and
                    figure.category in Figure.stock_list() and
                    check_same_date(figure.end_date, max_date)
                ):
                    filtered_figures.append(figure)

            event_aggregates.append({
                'name': event.name,
                'idps_reference_date': max_date.strftime('%Y-%m-%d'),
                **get_figure_aggregations(filtered_figures),
            })

        query = '''
            query MyQuery {
              eventList(ordering: "id") {
                results {
                  id
                  name
                  eventType
                  stockIdpFiguresMaxEndDate
                  totalStockIdpFigures
                  totalFlowNdFigures
                }
              }
            }
        '''
        r_data = self.query(query).json()['data']['eventList']['results']
        system_data = [
            {
                'name': i['name'],
                'idps_reference_date': i['stockIdpFiguresMaxEndDate'],
                'disaster_idps': i['totalStockIdpFigures'] if i['eventType'] == 'DISASTER' else None,
                'disaster_nds': i['totalFlowNdFigures'] if i['eventType'] == 'DISASTER' else None,
                'conflict_idps': i['totalStockIdpFigures'] if i['eventType'] == 'CONFLICT' else None,
                'conflict_nds': i['totalFlowNdFigures'] if i['eventType'] == 'CONFLICT' else None,
            }
            for i in r_data
        ]
        assert event_aggregates == system_data

    def test_figure_aggregation_in_crises(self):
        crisis_aggregates = []
        for crisis in self.crises:
            max_date = max([
                figure.end_date for figure in self.figures
                if (
                    figure.event.crisis == crisis and
                    figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
                    figure.role == Figure.ROLE.RECOMMENDED
                )
            ])
            filtered_figures = []
            for figure in self.figures:
                if (
                    figure.event.crisis == crisis and
                    figure.category in Figure.flow_list()
                ):
                    filtered_figures.append(figure)
                elif (
                    figure.event.crisis == crisis and
                    figure.category in Figure.stock_list() and
                    check_same_date(figure.end_date, max_date)
                ):
                    filtered_figures.append(figure)

            crisis_aggregates.append({
                'name': crisis.name,
                'idps_reference_date': max_date.strftime('%Y-%m-%d'),
                **get_figure_aggregations(filtered_figures),
            })

        query = '''
            query MyQuery {
              crisisList(ordering: "id") {
                results {
                  id
                  name
                  crisisType
                  stockIdpFiguresMaxEndDate
                  totalStockIdpFigures
                  totalFlowNdFigures
                }
              }
            }
        '''
        r_data = self.query(query).json()['data']['crisisList']['results']
        system_data = [
            {
                'name': i['name'],
                'idps_reference_date': i['stockIdpFiguresMaxEndDate'],
                'disaster_idps': i['totalStockIdpFigures'] if i['crisisType'] == 'DISASTER' else None,
                'disaster_nds': i['totalFlowNdFigures'] if i['crisisType'] == 'DISASTER' else None,
                'conflict_idps': i['totalStockIdpFigures'] if i['crisisType'] == 'CONFLICT' else None,
                'conflict_nds': i['totalFlowNdFigures'] if i['crisisType'] == 'CONFLICT' else None,
            }
            for i in r_data
        ]
        assert crisis_aggregates == system_data

    def test_figure_aggregation_in_reports(self):
        report_aggregates = []
        for report in self.reports:
            filtered_figures = []
            for figure in self.figures:
                country = report.filter_figure_countries.all().first()
                if (
                    figure.category in Figure.flow_list() and
                    check_date_range_inside_date_range(
                        figure.start_date,
                        figure.end_date,
                        report.filter_figure_start_after,
                        report.filter_figure_end_before,
                    ) and (
                        not country or figure.country == country
                    )
                ):
                    filtered_figures.append(figure)
                elif (
                    figure.category in Figure.stock_list() and
                    check_same_date(
                        figure.end_date,
                        report.filter_figure_end_before,
                    ) and (
                        not country or figure.country == country
                    )
                ):
                    filtered_figures.append(figure)

            # FIXME: The country is not getting the correct type
            report_name = (
                f'GRID {report.filter_figure_start_after.year + 1}' if country is None else
                f'GRID {report.filter_figure_start_after.year  + 1} - {country.iso3}'
            )

            report_aggregates.append({
                'name': report_name,
                'start_date': report.filter_figure_start_after.strftime('%Y-%m-%d'),
                'end_date': report.filter_figure_end_before.strftime('%Y-%m-%d'),
                **get_figure_aggregations(filtered_figures),
            })

        query = '''
            query MyQuery {
              reportList(ordering: "id") {
                results {
                  id
                  name
                  filterFigureStartAfter
                  filterFigureEndBefore
                  totalDisaggregation {
                    totalStockConflictSum
                    totalFlowConflictSum
                    totalStockDisasterSum
                    totalFlowDisasterSum
                  }
                }
              }
            }
        '''
        r_data = self.query(query).json()['data']['reportList']['results']
        system_data = [
            {
                'name': i['name'],
                'start_date': i['filterFigureStartAfter'],
                'end_date': i['filterFigureEndBefore'],
                'disaster_idps': i['totalDisaggregation']['totalStockDisasterSum'],
                'disaster_nds': i['totalDisaggregation']['totalFlowDisasterSum'],
                'conflict_idps': i['totalDisaggregation']['totalStockConflictSum'],
                'conflict_nds': i['totalDisaggregation']['totalFlowConflictSum'],
            }
            for i in r_data
        ]
        assert report_aggregates == system_data

    def test_figure_inclusion_in_country(self):
        country_figure_ids = {}
        for country in self.countries:
            filtered_figures = []
            for figure in self.figures:
                if (figure.country == country):
                    filtered_figures.append(figure)
            country_figure_ids[country.pk] = [str(f.pk) for f in filtered_figures]

        query = '''
            query MyQuery($id: [ID!]) {
              figureList(
                  ordering: "id",
                  pageSize: 999999,
                  filters: {
                    filterFigureCountries: $id
                  }
              ) {
                totalCount
                results {
                  id
                }
              }
            }
        '''
        for country in self.countries:
            r_data = self.query(query, variables={'id': country.pk}).json()['data']['figureList']
            system_data = [i['id'] for i in r_data['results']]
            assert len(country_figure_ids[country.pk]) == r_data['totalCount']
            assert len(country_figure_ids[country.pk]) == len(system_data)
            assert set(country_figure_ids[country.pk]) == set(system_data)

    def test_figure_inclusion_in_event(self):
        event_figure_ids = {}
        for event in self.events:
            filtered_figures = []
            for figure in self.figures:
                if (figure.event == event):
                    filtered_figures.append(figure)
            event_figure_ids[event.pk] = [str(f.pk) for f in filtered_figures]

        query = '''
            query MyQuery($id: [ID!]) {
              figureList(
                  ordering: "id",
                  pageSize: 999999,
                  filters: {
                    filterFigureEvents: $id
                  }
              ) {
                totalCount
                results {
                  id
                }
              }
            }
        '''
        for event in self.events:
            r_data = self.query(query, variables={'id': event.pk}).json()['data']['figureList']
            system_data = [i['id'] for i in r_data['results']]
            assert len(event_figure_ids[event.pk]) == r_data['totalCount']
            assert len(event_figure_ids[event.pk]) == len(system_data)
            assert set(event_figure_ids[event.pk]) == set(system_data)

    def test_figure_inclusion_in_crisis(self):
        crisis_figure_ids = {}
        for crisis in self.crises:
            filtered_figures = []
            for figure in self.figures:
                if (figure.event.crisis == crisis):
                    filtered_figures.append(figure)
            crisis_figure_ids[crisis.pk] = [str(f.pk) for f in filtered_figures]

        query = '''
            query MyQuery($id: [ID!]) {
              figureList(
                  ordering: "id",
                  pageSize: 999999,
                  filters: {
                    filterFigureCrises: $id
                  }
              ) {
                totalCount
                results {
                  id
                }
              }
            }
        '''
        for crisis in self.crises:
            r_data = self.query(query, variables={'id': crisis.pk}).json()['data']['figureList']
            system_data = [i['id'] for i in r_data['results']]
            assert len(crisis_figure_ids[crisis.pk]) == r_data['totalCount']
            assert len(crisis_figure_ids[crisis.pk]) == len(system_data)
            assert set(crisis_figure_ids[crisis.pk]) == set(system_data)

    def test_figure_inclusion_in_report(self):
        report_figure_ids = {}
        for report in self.reports:
            filtered_figures = []
            for figure in self.figures:
                country = report.filter_figure_countries.all().first()
                if (
                    figure.category in Figure.flow_list() and
                    check_date_range_inside_date_range(
                        figure.start_date,
                        figure.end_date,
                        report.filter_figure_start_after,
                        report.filter_figure_end_before,
                    ) and (
                        not country or figure.country == country
                    )
                ):
                    filtered_figures.append(figure)
                elif (
                    figure.category in Figure.stock_list() and
                    check_date_inside_date_range(
                        figure.end_date,
                        report.filter_figure_start_after,
                        report.filter_figure_end_before,
                    ) and (
                        not country or figure.country == country
                    )
                ):
                    filtered_figures.append(figure)

            report_figure_ids[report.pk] = [str(f.pk) for f in filtered_figures]

        query = '''
            query MyQuery($id: String!) {
              figureList(
                  ordering: "id",
                  pageSize: 999999,
                  filters: {
                    reportId: $id
                  }
              ) {
                totalCount
                results {
                  id
                }
              }
            }
        '''
        for report in self.reports:
            r_data = self.query(query, variables={'id': report.pk}).json()['data']['figureList']
            system_data = [i['id'] for i in r_data['results']]
            assert len(report_figure_ids[report.pk]) == r_data['totalCount']
            assert len(report_figure_ids[report.pk]) == len(system_data)
            assert set(report_figure_ids[report.pk]) == set(system_data)

    def test_crisis_inclusion_in_country(self):
        # NOTE: We need to check if crisis is included in country
        # We should also aggregate the figures for crisis
        pass

    def test_event_inclusion_in_country(self):
        # NOTE: We need to check if event is included in country
        # We should also aggregate the figures for event
        pass

    def test_event_inclusion_in_crisis(self):
        # NOTE: We need to check if event is included in crisis
        # We should also aggregate the figures for event
        pass

    def test_country_inclusion_in_report(self):
        # NOTE: We need to check if country is included in report
        # We should also aggregate the figures for country
        pass

    def test_crisis_inclusion_in_report(self):
        # NOTE: We need to check if crisis is included in report
        # We should also aggregate the figures for crisis
        pass

    def test_event_inclusion_in_report(self):
        # NOTE: We need to check if event is included in report
        # We should also aggregate the figures for event
        pass

    def test_gidd_conflict(self):
        pass

    def test_gidd_disaster(self):
        pass

    def test_gidd_displacement(self):
        pass
