import typing
import functools
import mock
import logging
from datetime import date, timedelta, datetime
from random import randint
from math import sqrt
from itertools import groupby

from utils.factories import (
    EventFactory,
    CrisisFactory,
    CountryFactory,
    FigureFactory,
    EntryFactory,
    ReportFactory,
)
from apps.contrib.models import Client
from apps.crisis.models import Crisis
from apps.event.models import Event
from apps.entry.models import Figure, Entry
from apps.report.models import Report
from apps.country.models import Country
from apps.users.enums import USER_ROLE
from apps.gidd.tasks import update_gidd_data
from apps.gidd.models import ReleaseMetadata, StatusLog
from utils.tests import (
    HelixGraphQLTestCase,
    create_user_with_role,
)

logger = logging.getLogger(__name__)


def get_safe_max(lst: typing.List[date]):
    if lst:
        return max(lst)


def get_safe_sum(lst: typing.List[int]):
    '''If the list is empty or None, sum should be None'''
    if lst:
        return sum(lst)


def get_figure_aggregations(figures: typing.List[Figure]):
    return {
        'disaster_idps': get_safe_sum([
            figure.total_figures for figure in figures
            if (
                figure.event.event_type == Crisis.CRISIS_TYPE.DISASTER and
                figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
                figure.role == Figure.ROLE.RECOMMENDED
            )
        ]),
        'disaster_nds': get_safe_sum([
            figure.total_figures for figure in figures
            if (
                figure.event.event_type == Crisis.CRISIS_TYPE.DISASTER and
                figure.category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT and
                figure.role == Figure.ROLE.RECOMMENDED
            )
        ]),
        'conflict_idps': get_safe_sum([
            figure.total_figures for figure in figures
            if (
                figure.event.event_type == Crisis.CRISIS_TYPE.CONFLICT and
                figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
                figure.role == Figure.ROLE.RECOMMENDED
            )
        ]),
        'conflict_nds': get_safe_sum([
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


class RuntimeProfile:
    label: str
    start: typing.Optional[datetime]

    def __init__(self, label: str = 'N/A'):
        self.label = label
        self.start = None

    def __call__(self, func):
        self.label = func.__name__

        @functools.wraps(func)
        def decorated(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return decorated

    def __enter__(self):
        self.start = datetime.now()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        assert self.start is not None
        time_delta = datetime.now() - self.start
        logger.info(f'Runtime with <{self.label}>: {time_delta}')


class TestCoreData(HelixGraphQLTestCase):

    @mock.patch('utils.graphene.pagination.get_page_size', lambda *_: 999999)
    def query_json(self, query: str, variables: typing.Optional[dict] = None) -> dict:
        with RuntimeProfile(str(variables)):
            response = self.query(query, variables=variables)
        self.assertResponseNoErrors(response)
        return response.json()

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
        ReleaseMetadata.objects.all().delete()

        cls.start_year = start_year = 2016
        cls.end_year = end_year = 2019

        # Country
        cls.country_npl = country_npl = CountryFactory.create(iso3='NPL', name="Nepal")
        cls.country_ind = country_ind = CountryFactory.create(iso3='IND', name="India")
        cls.countries = countries = [country_npl, country_ind]

        # User
        cls.admin = create_user_with_role(
            USER_ROLE.ADMIN.name,
        )

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
        # NOTE: This is empty crisis
        crises_5 = CrisisFactory.create(
            name='Crises-5',
            crisis_type=Crisis.CRISIS_TYPE.DISASTER,
        )
        crises_5.countries.add(country_ind)
        # NOTE: This is empty crisis
        crises_6 = CrisisFactory.create(
            name='Crises-6',
            crisis_type=Crisis.CRISIS_TYPE.DISASTER,
        )
        crises_6.countries.add(country_ind)
        cls.all_crises = [crises_1, crises_2, crises_3, crises_4, crises_5, crises_6]

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
        # Empty Event
        event_8 = EventFactory.create(
            name='Event-8',
            crisis=None,
            event_type=Crisis.CRISIS_TYPE.DISASTER,
            countries=[country_npl],
            actor=None,
        )
        # Empty Event
        event_9 = EventFactory.create(
            name='Event-9',
            crisis=None,
            event_type=Crisis.CRISIS_TYPE.CONFLICT,
            countries=[country_ind],
            actor=None,
        )
        # Empty Event
        event_10 = EventFactory.create(
            name='Event-10',
            crisis=None,
            event_type=Crisis.CRISIS_TYPE.OTHER,
            countries=[country_npl],
            actor=None,
        )
        # Empty Event referencing a crisis
        event_11: Event = EventFactory.create(
            name='Event-11',
            crisis=crises_1,
            event_type=crises_1.crisis_type,
            countries=[country_npl],
            actor=None,
        )
        cls.events = events = [event_1, event_2, event_3, event_4, event_5, event_6, event_7]
        cls.all_events = [*events, event_8, event_9, event_10, event_11]

        # Reports
        cls.reports: list[Report] = []
        cls.report_country_mapping = {}
        report_data_set: typing.List[typing.Tuple[int, typing.Union[None, Country]]] = [
            (year, country)
            for year in range(start_year, end_year + 1)
            for country in [None, *countries]
        ]
        for year, country in report_data_set:
            # NOTE: we only have full year reports with and without countries
            # Full year reports without countries are GIDD reports
            is_gidd_report = not country
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
                is_gidd_report=is_gidd_report,
                gidd_report_year=report_start_date.year if is_gidd_report else None
            )
            if country:
                report.filter_figure_countries.set([country])
                cls.report_country_mapping[report.pk] = country

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
        cls.figures = list(
            Figure.objects.all().select_related('event', 'event__crisis', 'country')
        )

        # Generate GIDD data
        cls.gidd_client = Client.objects.create(
            name='James Bond',
            code='BOND-007',
            is_active=True,
        )

        ReleaseMetadata.objects.create(
            release_year=cls.end_year,
            pre_release_year=cls.end_year - 1,
            modified_by=cls.admin,
            modified_at=datetime.now(),
        )
        status_log = StatusLog.objects.create(
            triggered_by=cls.admin,
            triggered_at=datetime.now(),
        )
        update_gidd_data(status_log.pk)

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.init_data()

    def setUp(self) -> None:
        super().setUp()
        self.user_monitoring_expert = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT.name,
            country=self.country_npl.pk,
        )
        self.force_login(self.user_monitoring_expert)

    @RuntimeProfile()
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
                query CountryList($year: Float!) {
                  countryList(
                      ordering: "id",
                      filters: {
                          aggregateFigures: {year: $year}
                      },
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
            response = self.query_json(query, variables={'year': year})
            r_data = response['data']['countryList']['results']
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

    @RuntimeProfile()
    def test_figure_aggregation_in_events(self):
        event_aggregates = {}
        for event in self.all_events:
            max_date = get_safe_max([
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
                    max_date and
                    figure.event == event and
                    figure.category in Figure.stock_list() and
                    check_same_date(figure.end_date, max_date)
                ):
                    filtered_figures.append(figure)

            event_aggregates[event.pk] = {
                'name': event.name,
                'idps_reference_date': max_date.strftime('%Y-%m-%d') if max_date else None,
                **get_figure_aggregations(filtered_figures),
            }
        events = [
            {
                **event_aggregates[event.pk],
                'name': event.name,
                'id': str(event.pk),
            }
            for event in self.all_events
        ]

        query = '''
            query EventList{
              eventList(
                ordering: "id",
              ) {
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
        response = self.query_json(query)
        r_data = response['data']['eventList']['results']
        system_data = [
            {
                'id': i['id'],
                'name': i['name'],
                'idps_reference_date': i['stockIdpFiguresMaxEndDate'],
                'disaster_idps': i['totalStockIdpFigures'] if i['eventType'] == 'DISASTER' else None,
                'disaster_nds': i['totalFlowNdFigures'] if i['eventType'] == 'DISASTER' else None,
                'conflict_idps': i['totalStockIdpFigures'] if i['eventType'] == 'CONFLICT' else None,
                'conflict_nds': i['totalFlowNdFigures'] if i['eventType'] == 'CONFLICT' else None,
            }
            for i in r_data
        ]
        assert events == system_data

    @RuntimeProfile()
    def test_figure_aggregation_in_crises(self):
        crisis_aggregates = {}
        for crisis in self.all_crises:
            max_date = get_safe_max([
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
                    max_date and
                    figure.event.crisis == crisis and
                    figure.category in Figure.stock_list() and
                    check_same_date(figure.end_date, max_date)
                ):
                    filtered_figures.append(figure)

            crisis_aggregates[crisis.pk] = {
                'id': crisis.pk,
                'name': crisis.name,
                'idps_reference_date': max_date.strftime('%Y-%m-%d') if max_date else None,
                **get_figure_aggregations(filtered_figures),
            }
        crises = [
            {
                **crisis_aggregates[crisis.pk],
                'name': crisis.name,
                'id': str(crisis.pk),
            }
            for crisis in self.all_crises
        ]

        query = '''
            query CrisisList{
              crisisList(
                ordering: "id",
              ) {
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
        response = self.query_json(query)
        r_data = response['data']['crisisList']['results']
        system_data = [
            {
                'id': i['id'],
                'name': i['name'],
                'idps_reference_date': i['stockIdpFiguresMaxEndDate'],
                'disaster_idps': i['totalStockIdpFigures'] if i['crisisType'] == 'DISASTER' else None,
                'disaster_nds': i['totalFlowNdFigures'] if i['crisisType'] == 'DISASTER' else None,
                'conflict_idps': i['totalStockIdpFigures'] if i['crisisType'] == 'CONFLICT' else None,
                'conflict_nds': i['totalFlowNdFigures'] if i['crisisType'] == 'CONFLICT' else None,
            }
            for i in r_data
        ]
        assert crises == system_data

    @RuntimeProfile()
    def test_figure_aggregation_in_reports(self):
        report_aggregates = []
        for report in self.reports:
            country = self.report_country_mapping.get(report.pk)
            filtered_figures = []
            for figure in self.figures:
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
            query ReportList{
              reportList(
                ordering: "id",
              ) {
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
        response = self.query_json(query)
        r_data = response['data']['reportList']['results']
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

    @RuntimeProfile()
    def test_figure_inclusion_in_country(self):
        country_figure_ids = {}
        for country in self.countries:
            filtered_figures = []
            for figure in self.figures:
                if (figure.country == country):
                    filtered_figures.append(figure)
            country_figure_ids[country.pk] = [str(f.pk) for f in filtered_figures]

        query = '''
            query FigureListForCountry($id: [ID!]) {
              figureList(
                  ordering: "id",
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
            response = self.query_json(query, variables={'id': country.pk})
            r_data = response['data']['figureList']
            system_data = [i['id'] for i in r_data['results']]
            assert len(country_figure_ids[country.pk]) == r_data['totalCount']
            assert len(country_figure_ids[country.pk]) == len(system_data)
            assert set(country_figure_ids[country.pk]) == set(system_data)

    @RuntimeProfile()
    def test_crisis_inclusion_in_country(self):
        for country in self.countries:
            filtered_crises = []
            crisis_aggregates = {}
            for crisis in self.all_crises:
                if country not in crisis.countries.all():
                    continue

                filtered_crises.append(crisis)

                max_date = get_safe_max([
                    figure.end_date for figure in self.figures
                    if (
                        figure.country == country and
                        figure.event.crisis == crisis and
                        figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
                        figure.role == Figure.ROLE.RECOMMENDED
                    )
                ])
                filtered_figures = []
                for figure in self.figures:
                    if (
                        figure.country == country and
                        figure.event.crisis == crisis and
                        figure.category in Figure.flow_list()
                    ):
                        filtered_figures.append(figure)
                    elif (
                        figure.country == country and
                        max_date and
                        figure.event.crisis == crisis and
                        figure.category in Figure.stock_list() and
                        check_same_date(figure.end_date, max_date)
                    ):
                        filtered_figures.append(figure)

                crisis_aggregates[crisis.pk] = {
                    'id': crisis.pk,
                    'name': crisis.name,
                    'idps_reference_date': max_date.strftime('%Y-%m-%d') if max_date else None,
                    **get_figure_aggregations(filtered_figures),
                }

            crises = [
                {
                    **crisis_aggregates[crisis.pk],
                    'name': crisis.name,
                    'id': str(crisis.pk),
                }
                for crisis in filtered_crises
            ]

            query = '''
                query CrisisListForCountry($countries: [ID!]){
                  crisisList(
                      ordering: "id",
                      filters: {
                        countries: $countries,
                        filterFigures: {
                            # filterFigureCountries: $countries
                        },
                        aggregateFigures: {
                            filterFigures: {
                                filterFigureCountries: $countries,
                            },
                        },
                      }
                  ) {
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
            response = self.query_json(query, variables={'countries': [country.pk]})
            r_data = response['data']['crisisList']['results']
            system_data = [
                {
                    'id': i['id'],
                    'name': i['name'],
                    'idps_reference_date': i['stockIdpFiguresMaxEndDate'],
                    'disaster_idps': i['totalStockIdpFigures'] if i['crisisType'] == 'DISASTER' else None,
                    'disaster_nds': i['totalFlowNdFigures'] if i['crisisType'] == 'DISASTER' else None,
                    'conflict_idps': i['totalStockIdpFigures'] if i['crisisType'] == 'CONFLICT' else None,
                    'conflict_nds': i['totalFlowNdFigures'] if i['crisisType'] == 'CONFLICT' else None,
                }
                for i in r_data
            ]
            assert crises == system_data

    @RuntimeProfile()
    def test_event_inclusion_in_country(self):
        for country in self.countries:
            filtered_events = []
            event_aggregates = {}
            for event in self.all_events:
                if country not in event.countries.all():
                    continue

                filtered_events.append(event)

                max_date = get_safe_max([
                    figure.end_date for figure in self.figures
                    if (
                        figure.country == country and
                        figure.event == event and
                        figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
                        figure.role == Figure.ROLE.RECOMMENDED
                    )
                ])
                filtered_figures = []
                for figure in self.figures:
                    if (
                        figure.country == country and
                        figure.event == event and
                        figure.category in Figure.flow_list()
                    ):
                        filtered_figures.append(figure)
                    elif (
                        figure.country == country and
                        max_date and
                        figure.event == event and
                        figure.category in Figure.stock_list() and
                        check_same_date(figure.end_date, max_date)
                    ):
                        filtered_figures.append(figure)

                event_aggregates[event.pk] = {
                    'id': event.pk,
                    'name': event.name,
                    'idps_reference_date': max_date.strftime('%Y-%m-%d') if max_date else None,
                    **get_figure_aggregations(filtered_figures),
                }

            events = [
                {
                    **event_aggregates[event.pk],
                    'name': event.name,
                    'id': str(event.pk),
                }
                for event in filtered_events
            ]

            query = '''
                query EventListForCountry($countries: [ID!]){
                  eventList(
                      ordering: "id",
                      filters: {
                        countries: $countries,
                        filterFigures: {
                            # filterFigureCountries: $countries
                        },
                        aggregateFigures: {
                            filterFigures: {
                                filterFigureCountries: $countries,
                            },
                        },
                      }
                  ) {
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
            response = self.query_json(query, variables={'countries': [country.pk]})
            r_data = response['data']['eventList']['results']
            system_data = [
                {
                    'id': i['id'],
                    'name': i['name'],
                    'idps_reference_date': i['stockIdpFiguresMaxEndDate'],
                    'disaster_idps': i['totalStockIdpFigures'] if i['eventType'] == 'DISASTER' else None,
                    'disaster_nds': i['totalFlowNdFigures'] if i['eventType'] == 'DISASTER' else None,
                    'conflict_idps': i['totalStockIdpFigures'] if i['eventType'] == 'CONFLICT' else None,
                    'conflict_nds': i['totalFlowNdFigures'] if i['eventType'] == 'CONFLICT' else None,
                }
                for i in r_data
            ]
            assert events == system_data

    @RuntimeProfile()
    def test_figure_inclusion_in_event(self):
        event_figure_ids = {}
        for event in self.all_events:
            filtered_figures = []
            for figure in self.figures:
                if (figure.event == event):
                    filtered_figures.append(figure)
            event_figure_ids[event.pk] = [str(f.pk) for f in filtered_figures]

        query = '''
            query FigureListForEvent($id: [ID!]) {
              figureList(
                  ordering: "id",
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
        for event in self.all_events:
            response = self.query_json(query, variables={'id': event.pk})
            r_data = response['data']['figureList']
            system_data = [i['id'] for i in r_data['results']]
            assert len(event_figure_ids[event.pk]) == r_data['totalCount']
            assert len(event_figure_ids[event.pk]) == len(system_data)
            assert set(event_figure_ids[event.pk]) == set(system_data)

    @RuntimeProfile()
    def test_country_inclusion_in_event(self):
        for event in self.all_events:
            for year in range(self.start_year, self.end_year + 1):
                filtered_countries = []
                country_aggregates = {}
                for country in self.countries:
                    if country not in event.countries.all():
                        continue

                    filtered_countries.append(country)

                    filtered_figures = []
                    for figure in self.figures:
                        if (
                            figure.event == event and
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
                            figure.event == event and
                            figure.country == country and
                            figure.category in Figure.stock_list() and
                            check_same_date(figure.end_date, date(year, 12, 31))
                        ):
                            filtered_figures.append(figure)

                    country_aggregates[country.pk] = {
                        'iso3': country.iso3,
                        **get_figure_aggregations(filtered_figures),
                    }

                countries = [
                    {
                        **country_aggregates[country.pk],
                        'iso3': country.iso3,
                        'id': str(country.pk),
                    }
                    for country in filtered_countries
                ]

                query = '''
                    query CountryListForEvent($year: Float!, $events: [ID!]) {
                      countryList(
                          ordering: "id",
                          filters: {
                              events: $events
                              filterFigures: {}
                              aggregateFigures: {
                                  year: $year
                                  filterFigures: {
                                    filterFigureEvents: $events
                                  }
                              }
                          },
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
                response = self.query_json(query, variables={'year': year, 'events': [event.pk]})
                r_data = response['data']['countryList']['results']
                system_data = [
                    {
                        'id': i['id'],
                        'iso3': i['iso3'],
                        'disaster_idps': i['totalStockDisaster'],
                        'disaster_nds': i['totalFlowDisaster'],
                        'conflict_idps': i['totalStockConflict'],
                        'conflict_nds': i['totalFlowConflict'],
                    }
                    for i in r_data
                ]
                assert countries == system_data

    @RuntimeProfile()
    def test_figure_inclusion_in_crisis(self):
        crisis_figure_ids = {}
        for crisis in self.all_crises:
            filtered_figures = []
            for figure in self.figures:
                if (figure.event.crisis == crisis):
                    filtered_figures.append(figure)
            crisis_figure_ids[crisis.pk] = [str(f.pk) for f in filtered_figures]

        query = '''
            query FigureListForCrisis($id: [ID!]) {
              figureList(
                  ordering: "id",
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
        for crisis in self.all_crises:
            response = self.query_json(query, variables={'id': crisis.pk})
            r_data = response['data']['figureList']
            system_data = [i['id'] for i in r_data['results']]
            assert len(crisis_figure_ids[crisis.pk]) == r_data['totalCount']
            assert len(crisis_figure_ids[crisis.pk]) == len(system_data)
            assert set(crisis_figure_ids[crisis.pk]) == set(system_data)

    @RuntimeProfile()
    def test_country_inclusion_in_crisis(self):
        for crisis in self.all_crises:
            for year in range(self.start_year, self.end_year + 1):
                filtered_countries = []
                country_aggregates = {}
                for country in self.countries:
                    if country not in crisis.countries.all():
                        continue

                    filtered_countries.append(country)

                    filtered_figures = []
                    for figure in self.figures:
                        if (
                            figure.event.crisis == crisis and
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
                            figure.event.crisis == crisis and
                            figure.country == country and
                            figure.category in Figure.stock_list() and
                            check_same_date(figure.end_date, date(year, 12, 31))
                        ):
                            filtered_figures.append(figure)

                    country_aggregates[country.pk] = {
                        'iso3': country.iso3,
                        **get_figure_aggregations(filtered_figures),
                    }

                countries = [
                    {
                        **country_aggregates[country.pk],
                        'iso3': country.iso3,
                        'id': str(country.pk),
                    }
                    for country in filtered_countries
                ]

                query = '''
                    query CountryListForCrisis($year: Float!, $crises: [ID!]) {
                      countryList(
                          ordering: "id",
                          filters: {
                              crises: $crises
                              filterFigures: {}
                              aggregateFigures: {
                                  year: $year
                                  filterFigures: {
                                    filterFigureCrises: $crises
                                  }
                              }
                          },
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
                response = self.query_json(query, variables={'year': year, 'crises': [crisis.pk]})
                r_data = response['data']['countryList']['results']
                system_data = [
                    {
                        'id': i['id'],
                        'iso3': i['iso3'],
                        'disaster_idps': i['totalStockDisaster'],
                        'disaster_nds': i['totalFlowDisaster'],
                        'conflict_idps': i['totalStockConflict'],
                        'conflict_nds': i['totalFlowConflict'],
                    }
                    for i in r_data
                ]
                assert countries == system_data

    @RuntimeProfile()
    def test_event_inclusion_in_crisis(self):
        for crisis in self.all_crises:
            filtered_events = []
            event_aggregates = {}
            for event in self.all_events:
                if event.crisis != crisis:
                    continue

                filtered_events.append(event)

                max_date = get_safe_max([
                    figure.end_date for figure in self.figures
                    if (
                        figure.event.crisis == crisis and
                        figure.event == event and
                        figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
                        figure.role == Figure.ROLE.RECOMMENDED
                    )
                ])
                filtered_figures = []
                for figure in self.figures:
                    if (
                        figure.event.crisis == crisis and
                        figure.event == event and
                        figure.category in Figure.flow_list()
                    ):
                        filtered_figures.append(figure)
                    elif (
                        figure.event.crisis == crisis and
                        max_date and
                        figure.event == event and
                        figure.category in Figure.stock_list() and
                        check_same_date(figure.end_date, max_date)
                    ):
                        filtered_figures.append(figure)

                event_aggregates[event.pk] = {
                    'id': event.pk,
                    'name': event.name,
                    'idps_reference_date': max_date.strftime('%Y-%m-%d') if max_date else None,
                    **get_figure_aggregations(filtered_figures),
                }

            events = [
                {
                    **event_aggregates[event.pk],
                    'name': event.name,
                    'id': str(event.pk),
                }
                for event in filtered_events
            ]

            query = '''
                query EventListForCrisis($crises: [ID!]){
                  eventList(
                      ordering: "id",
                      filters: {
                        crisisByIds: $crises,
                        filterFigures: {
                            # filterFigureCrises: $crises,
                        },
                        aggregateFigures: {
                            filterFigures: {
                                filterFigureCrises: $crises,
                            },
                        },
                      }
                  ) {
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
            response = self.query_json(query, variables={'crises': [crisis.pk]})
            r_data = response['data']['eventList']['results']
            system_data = [
                {
                    'id': i['id'],
                    'name': i['name'],
                    'idps_reference_date': i['stockIdpFiguresMaxEndDate'],
                    'disaster_idps': i['totalStockIdpFigures'] if i['eventType'] == 'DISASTER' else None,
                    'disaster_nds': i['totalFlowNdFigures'] if i['eventType'] == 'DISASTER' else None,
                    'conflict_idps': i['totalStockIdpFigures'] if i['eventType'] == 'CONFLICT' else None,
                    'conflict_nds': i['totalFlowNdFigures'] if i['eventType'] == 'CONFLICT' else None,
                }
                for i in r_data
            ]
            assert events == system_data

    @RuntimeProfile()
    def test_figure_inclusion_in_report(self):
        report_figure_ids = {}
        for report in self.reports:
            filtered_figures = []
            country = self.report_country_mapping.get(report.pk)
            for figure in self.figures:
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
            query FigureListForReport($id: ID!) {
              figureList(
                  ordering: "id",
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
            response = self.query_json(query, variables={'id': report.pk})
            r_data = response['data']['figureList']
            system_data = [i['id'] for i in r_data['results']]
            assert len(report_figure_ids[report.pk]) == r_data['totalCount']
            assert len(report_figure_ids[report.pk]) == len(system_data)
            assert set(report_figure_ids[report.pk]) == set(system_data)

    @RuntimeProfile()
    def test_crisis_inclusion_in_report(self):
        for report in self.reports:
            country = self.report_country_mapping.get(report.pk)
            crisis_aggregates = []
            for crisis in self.all_crises:
                filtered_figures = []
                for figure in self.figures:
                    if (
                        figure.event.crisis == crisis and
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
                        figure.event.crisis == crisis and
                        figure.category in Figure.stock_list() and
                        check_same_date(
                            figure.end_date,
                            report.filter_figure_end_before,
                        ) and (
                            not country or figure.country == country
                        )
                    ):
                        filtered_figures.append(figure)

                if len(filtered_figures) > 0:
                    crisis_aggregates.append({
                        'id': str(crisis.pk),
                        'name': crisis.name,
                        **get_figure_aggregations(filtered_figures),
                    })

            query = '''
                query crisisListForReport($reportId: ID!){
                  crisisList(
                      ordering: "id",
                      filters: {
                        filterFigures: {
                            reportId: $reportId,
                        },
                        aggregateFigures: {
                            filterFigures: {
                                reportId: $reportId,
                            },
                        },
                      }
                  ) {
                    results {
                      id
                      name
                      crisisType
                      # stockIdpFiguresMaxEndDate
                      totalStockIdpFigures
                      totalFlowNdFigures
                    }
                  }
                }
            '''
            response = self.query_json(query, variables={'reportId': report.pk})
            r_data = response['data']['crisisList']['results']
            system_data = [
                {
                    'id': i['id'],
                    'name': i['name'],
                    # 'idps_reference_date': i['stockIdpFiguresMaxEndDate'],
                    'disaster_idps': i['totalStockIdpFigures'] if i['crisisType'] == 'DISASTER' else None,
                    'disaster_nds': i['totalFlowNdFigures'] if i['crisisType'] == 'DISASTER' else None,
                    'conflict_idps': i['totalStockIdpFigures'] if i['crisisType'] == 'CONFLICT' else None,
                    'conflict_nds': i['totalFlowNdFigures'] if i['crisisType'] == 'CONFLICT' else None,
                }
                for i in r_data
            ]
            assert crisis_aggregates == system_data

    @RuntimeProfile()
    def test_event_inclusion_in_report(self):
        for report in self.reports:
            country = self.report_country_mapping.get(report.pk)
            event_aggregates = []
            for event in self.all_events:
                filtered_figures = []
                for figure in self.figures:
                    if (
                        figure.event == event and
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
                        figure.event == event and
                        figure.category in Figure.stock_list() and
                        check_same_date(
                            figure.end_date,
                            report.filter_figure_end_before,
                        ) and (
                            not country or figure.country == country
                        )
                    ):
                        filtered_figures.append(figure)

                if len(filtered_figures) > 0:
                    event_aggregates.append({
                        'id': str(event.pk),
                        'name': event.name,
                        **get_figure_aggregations(filtered_figures),
                    })

            query = '''
                query EventListForReport($reportId: ID!){
                  eventList(
                      ordering: "id",
                      filters: {
                        filterFigures: {
                            reportId: $reportId,
                        },
                        aggregateFigures: {
                            filterFigures: {
                                reportId: $reportId,
                            },
                        },
                      }
                  ) {
                    results {
                      id
                      name
                      eventType
                      # stockIdpFiguresMaxEndDate
                      totalStockIdpFigures
                      totalFlowNdFigures
                    }
                  }
                }
            '''
            response = self.query_json(query, variables={'reportId': report.pk})
            r_data = response['data']['eventList']['results']
            system_data = [
                {
                    'id': i['id'],
                    'name': i['name'],
                    # 'idps_reference_date': i['stockIdpFiguresMaxEndDate'],
                    'disaster_idps': i['totalStockIdpFigures'] if i['eventType'] == 'DISASTER' else None,
                    'disaster_nds': i['totalFlowNdFigures'] if i['eventType'] == 'DISASTER' else None,
                    'conflict_idps': i['totalStockIdpFigures'] if i['eventType'] == 'CONFLICT' else None,
                    'conflict_nds': i['totalFlowNdFigures'] if i['eventType'] == 'CONFLICT' else None,
                }
                for i in r_data
            ]
            assert event_aggregates == system_data

    @RuntimeProfile()
    def test_country_inclusion_in_report(self):
        for report in self.reports:
            report_country = self.report_country_mapping.get(report.pk)
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
                            report.filter_figure_start_after,
                            report.filter_figure_end_before,
                        ) and (
                            not report_country or figure.country == report_country
                        )
                    ):
                        filtered_figures.append(figure)
                    elif (
                        figure.country == country and
                        figure.category in Figure.stock_list() and
                        check_same_date(
                            figure.end_date,
                            report.filter_figure_end_before,
                        ) and (
                            not report_country or figure.country == report_country
                        )
                    ):
                        filtered_figures.append(figure)

                if len(filtered_figures) > 0:
                    country_aggregates.append({
                        'id': str(country.pk),
                        'iso3': country.iso3,
                        **get_figure_aggregations(filtered_figures),
                    })

            query = '''
                query countryListForReport($reportId: ID!){
                  countryList(
                      ordering: "id",
                      filters: {
                        filterFigures: {
                            reportId: $reportId,
                        },
                        aggregateFigures: {
                            filterFigures: {
                                reportId: $reportId,
                            },
                        },
                      }
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
            response = self.query_json(query, variables={'reportId': report.pk})
            r_data = response['data']['countryList']['results']
            system_data = [
                {
                    'id': i['id'],
                    'iso3': i['iso3'],
                    'disaster_idps': i['totalStockDisaster'],
                    'disaster_nds': i['totalFlowDisaster'],
                    'conflict_idps': i['totalStockConflict'],
                    'conflict_nds': i['totalFlowConflict'],
                }
                for i in r_data
            ]
            assert country_aggregates == system_data

    @RuntimeProfile()
    def test_gidd_displacement_data(self):
        displacement_data = []
        for year in range(self.start_year, self.end_year + 1):
            for country in self.countries:
                filtered_figures = []
                for figure in self.figures:
                    if (
                        figure.category in Figure.flow_list() and
                        figure.country == country and
                        check_date_range_inside_date_range(
                            figure.start_date,
                            figure.end_date,
                            date(year, 1, 1),
                            date(year, 12, 31),
                        )
                    ):
                        filtered_figures.append(figure)
                    elif (
                        figure.category in Figure.stock_list() and
                        figure.country == country and
                        check_same_date(
                            figure.end_date,
                            date(year, 12, 31),
                        )
                    ):
                        filtered_figures.append(figure)

                if filtered_figures:
                    displacement_data.append({
                        'year': year,
                        'iso3': country.iso3,
                        **get_figure_aggregations(filtered_figures),
                    })

        # NOTE: Both IDPs and NDs are summed if year is not provided
        overall_conflict_idps = get_safe_sum([
            row['conflict_idps']
            for row in displacement_data
            if row['conflict_idps'] is not None
        ])
        overall_conflict_nds = get_safe_sum([
            row['conflict_nds']
            for row in displacement_data
            if row['conflict_nds'] is not None
        ])
        overall_disaster_nds = get_safe_sum([
            row['disaster_nds']
            for row in displacement_data
            if row['disaster_nds'] is not None
        ])
        overall_disaster_idps = get_safe_sum([
            row['disaster_idps']
            for row in displacement_data
            if row['disaster_idps'] is not None
        ])

        query = '''
            query DisplacementData($clientId: String!){
                giddPublicDisplacements(
                    filters: {},
                    clientId: $clientId,
                ){
                    results {
                        conflictNewDisplacement
                        conflictTotalDisplacement
                        disasterNewDisplacement
                        disasterTotalDisplacement
                        id
                        iso3
                        year
                    }
                    totalCount
                    page
                    pageSize
                }
                giddPublicConflictStatistics(
                    clientId: $clientId,
                ){
                    newDisplacements
                    totalDisplacements
                }
                giddPublicDisasterStatistics(
                    clientId: $clientId,
                ){
                    newDisplacements
                    totalDisplacements
                }
                giddPublicCombinedStatistics(
                    clientId: $clientId,
                ) {
                    internalDisplacements
                    totalDisplacements
                }
            }
        '''
        response = self.query_json(query, variables={'clientId': self.gidd_client.code})
        r_data = response['data']['giddPublicDisplacements']['results']
        system_data = [
            {
                'iso3': i['iso3'],
                'year': i['year'],
                'disaster_idps': i['disasterTotalDisplacement'],
                'disaster_nds': i['disasterNewDisplacement'],
                'conflict_idps': i['conflictTotalDisplacement'],
                'conflict_nds': i['conflictNewDisplacement'],
            }
            for i in r_data
        ]
        assert displacement_data == system_data

        conflict_stats_r_data = response['data']['giddPublicConflictStatistics']
        disaster_stats_r_data = response['data']['giddPublicDisasterStatistics']
        combined_stats_r_data = response['data']['giddPublicCombinedStatistics']

        assert conflict_stats_r_data['newDisplacements'] == overall_conflict_nds
        assert disaster_stats_r_data['newDisplacements'] == overall_disaster_nds
        assert conflict_stats_r_data['totalDisplacements'] == overall_conflict_idps
        assert disaster_stats_r_data['totalDisplacements'] == overall_disaster_idps

        assert combined_stats_r_data['internalDisplacements'] == get_safe_sum([
            x
            for x in [overall_disaster_nds, overall_conflict_nds]
            if x is not None
        ])
        assert combined_stats_r_data['totalDisplacements'] == get_safe_sum([
            x
            for x in [overall_disaster_idps, overall_conflict_idps]
            if x is not None
        ])

    @RuntimeProfile()
    def test_gidd_disaster_data(self):
        disaster_data = []
        disaster_events = [
            event
            for event in self.events
            if event.event_type == Crisis.CRISIS_TYPE.DISASTER
        ]
        for year in range(self.start_year, self.end_year + 1):
            for country in self.countries:
                for event in disaster_events:
                    filtered_figures = []
                    for figure in self.figures:
                        if (
                            figure.event == event and
                            figure.category in Figure.flow_list() and
                            figure.country == country and
                            check_date_range_inside_date_range(
                                figure.start_date,
                                figure.end_date,
                                date(year, 1, 1),
                                date(year, 12, 31),
                            )
                        ):
                            filtered_figures.append(figure)
                        elif (
                            figure.event == event and
                            figure.category in Figure.stock_list() and
                            figure.country == country and
                            check_same_date(
                                figure.end_date,
                                date(year, 12, 31),
                            )
                        ):
                            filtered_figures.append(figure)

                    if filtered_figures:
                        disaster_data.append({
                            'id': str(event.id),
                            'year': year,
                            'iso3': country.iso3,
                            'event': event.name,
                            **get_figure_aggregations(filtered_figures),
                            'disaster_idps': None,
                        })

        query = '''
            query DisasterData($clientId: String!){
                giddPublicDisasters(
                    filters: {},
                    clientId: $clientId,
                ){
                    results {
                        id
                        eventId
                        eventName
                        year
                        iso3
                        newDisplacement
                    }
                    totalCount
                    page
                    pageSize
                }
            }
        '''
        response = self.query_json(query, variables={'clientId': self.gidd_client.code})
        r_data = response['data']['giddPublicDisasters']['results']
        system_data = [
            {
                'id': i['eventId'],
                'year': i['year'],
                'iso3': i['iso3'],
                'event': i['eventName'],

                'disaster_idps': None,
                'disaster_nds': i['newDisplacement'],
                'conflict_idps': None,
                'conflict_nds': None,
            }
            for i in r_data
        ]
        # NOTE: Removing idps as it's not generated in GIDD right now
        assert [{**row, 'disaster_idps': None} for row in disaster_data] == system_data

    @RuntimeProfile()
    def test_chart_aggregations(self):
        figures = [
            {
                'date': (
                    figure.start_date if figure.start_date.year == figure.end_date.year else figure.end_date
                ) if figure.category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT else figure.end_date,
                'cause': figure.figure_cause,
                'category': figure.category,
                'value': figure.total_figures,
            }
            for figure in self.figures
            if (
                figure.role == Figure.ROLE.RECOMMENDED and
                figure.category in [Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT, Figure.FIGURE_CATEGORY_TYPES.IDPS]
            )
        ]

        def aggregate_by_date(figures):
            def comparator(f):
                return f['date']

            by_date_dict = {
                k: get_safe_sum([f['value'] for f in list(v)])
                for k, v in groupby(sorted(figures, key=comparator), key=comparator)
            }
            return [{'date': k.strftime('%Y-%m-%d'), 'value': v} for k, v in by_date_dict.items()]

        # Let's filter to create 4 groups
        idps_disaster_figures = aggregate_by_date([
            f
            for f in figures
            if f['cause'] == Crisis.CRISIS_TYPE.DISASTER and
            f['category'] == Figure.FIGURE_CATEGORY_TYPES.IDPS
        ])
        idps_conflict_figures = aggregate_by_date([
            f
            for f in figures
            if f['cause'] == Crisis.CRISIS_TYPE.CONFLICT and
            f['category'] == Figure.FIGURE_CATEGORY_TYPES.IDPS
        ])
        nds_disaster_figures = aggregate_by_date([
            f
            for f in figures
            if f['cause'] == Crisis.CRISIS_TYPE.DISASTER and
            f['category'] == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT
        ])
        nds_conflict_figures = aggregate_by_date([
            f
            for f in figures
            if f['cause'] == Crisis.CRISIS_TYPE.CONFLICT and
            f['category'] == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT
        ])

        query = '''
            query FigureAggregations {
              figureAggregations(
                  filters: {}
              ) {
                idpsConflictFigures {
                  date
                  value
                }
                idpsDisasterFigures {
                  date
                  value
                }
                ndsDisasterFigures {
                  date
                  value
                }
                ndsConflictFigures {
                  date
                  value
                }
              }
            }
        '''
        response = self.query_json(query)
        r_data = response['data']['figureAggregations']

        assert idps_disaster_figures == r_data['idpsDisasterFigures']
        assert idps_conflict_figures == r_data['idpsConflictFigures']
        assert nds_disaster_figures == r_data['ndsDisasterFigures']
        assert nds_conflict_figures == r_data['ndsConflictFigures']
