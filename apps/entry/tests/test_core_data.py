import typing
from datetime import date, timedelta
from random import randint
from math import sqrt


from utils.factories import (
    EventFactory,
    CrisisFactory,
    CountryFactory,
    FigureFactory,
    EntryFactory,
    ReportFactory,
)
from apps.crisis.models import Crisis
from apps.event.models import Figure, Event
from apps.country.models import Country
from apps.users.enums import USER_ROLE
from utils.tests import (
    HelixGraphQLTestCase,
    create_user_with_role,
)


def flow_inside_range(start_date: date, end_date: date, start_date_range: date, end_date_range: date) -> bool:
    if start_date.year != end_date.year:
        return start_date_range <= end_date <= end_date_range
    return start_date_range <= start_date <= end_date_range


def stock_inside_range(stock_reporting_date: date, end_date_range: date) -> bool:
    return stock_reporting_date == end_date_range


def is_prime(n: int):
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


def prime_generator():
    # NOTE: Let's start with 3
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


def get_figure_value_sum(figures):
    if figures:
        return sum(figures)


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


class TestCoreData(HelixGraphQLTestCase):
    @classmethod
    def init_data(cls):
        # Start from scratch
        # TODO: Find out why we have initial data before this.
        Country.objects.all().delete()
        Crisis.objects.all().delete()
        Event.objects.all().delete()
        # Country
        cls.country_npl = country_npl = CountryFactory.create(iso3='NPL')
        cls.country_ind = country_ind = CountryFactory.create(iso3='IND')
        # Crisis
        crises_1 = CrisisFactory.create(name='Crises-1', crisis_type=Crisis.CRISIS_TYPE.DISASTER)
        crises_2 = CrisisFactory.create(name='Crises-2', crisis_type=Crisis.CRISIS_TYPE.CONFLICT)
        cls.crises = [crises_1, crises_2]
        # NOTE: For now global entry
        entry = EntryFactory.create()
        # Events
        event_1 = EventFactory.create(name='Event-1', crisis=crises_1, event_type=crises_1.crisis_type)
        event_2 = EventFactory.create(name='Event-2', crisis=crises_1, event_type=crises_1.crisis_type)
        event_3 = EventFactory.create(name='Event-3', crisis=crises_2, event_type=crises_2.crisis_type)
        event_4 = EventFactory.create(name='Event-4', crisis=crises_2, event_type=crises_2.crisis_type)
        cls.events = events = [event_1, event_2, event_3, event_4]

        # Figures
        figures = []
        for year in [2010, 2011, 2012, 2013]:
            for role in [Figure.ROLE.RECOMMENDED, Figure.ROLE.TRIANGULATION]:
                for country in [country_npl, country_ind]:
                    for event in events:
                        FIGURE_DATA_GENERATION_SET: typing.List[
                            typing.Tuple[
                                Figure.FIGURE_CATEGORY_TYPES,
                                GetDatesTypes,
                            ]
                        ]
                        if year == 2013:
                            FIGURE_DATA_GENERATION_SET = [
                                # Internal Displacement
                                (Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT, 'single_year_not_touching'),
                                # IDPs
                                (Figure.FIGURE_CATEGORY_TYPES.IDPS, 'single_year_not_touching'),
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
                            ]
                        # Start creating Figures
                        for figure_category, get_date_type in FIGURE_DATA_GENERATION_SET:
                            figure_kwargs = dict(
                                event=event,
                                entry=entry,
                                country=country,
                                role=role,
                                category=figure_category,
                                **get_dates(get_date_type, year),
                            )
                            # NOTE: We need to add iterations such that we have at
                            # least 2 values for each date
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
        self.user_monitoring_expert = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(self.user_monitoring_expert)

    def test_event_data(self):
        # Excepted Reports
        event_reports = []
        for event in self.events:
            max_date = max([
                figure.end_date for figure in self.figures
                if (
                    figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
                    figure.role == Figure.ROLE.RECOMMENDED and
                    figure.event == event
                )
            ])
            filtered_figures = []
            for figure in self.figures:
                if (
                    figure.category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT and
                    figure.role == Figure.ROLE.RECOMMENDED and
                    figure.event == event
                ):
                    filtered_figures.append(figure)
                elif (
                    figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
                    figure.role == Figure.ROLE.RECOMMENDED and
                    figure.event == event and
                    stock_inside_range(figure.end_date, max_date)
                ):
                    filtered_figures.append(figure)
            disaster_idps = get_figure_value_sum([
                figure.total_figures for figure in filtered_figures
                if (
                    figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
                    figure.event.event_type == Crisis.CRISIS_TYPE.DISASTER
                )
            ])
            disaster_nds = get_figure_value_sum([
                figure.total_figures for figure in filtered_figures
                if (
                    figure.category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT and
                    figure.event.event_type == Crisis.CRISIS_TYPE.DISASTER
                )
            ])
            conflict_idps = get_figure_value_sum([
                figure.total_figures for figure in filtered_figures
                if (
                    figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
                    figure.event.event_type == Crisis.CRISIS_TYPE.CONFLICT
                )
            ])
            conflict_nds = get_figure_value_sum([
                figure.total_figures for figure in filtered_figures
                if (
                    figure.category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT and
                    figure.event.event_type == Crisis.CRISIS_TYPE.CONFLICT
                )
            ])
            event_reports.append({
                'name': event.name,
                'idps_reference_date': max_date.strftime('%Y-%m-%d'),
                'disaster_idps': disaster_idps,
                'conflict_idps': conflict_idps,
                'disaster_nds': disaster_nds,
                'conflict_nds': conflict_nds,
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
        assert event_reports == system_data

    def test_crisis_data(self):
        # Excepted Crisis Reports
        crisis_reports = []
        for crisis in self.crises:
            max_date = max([
                figure.end_date for figure in self.figures
                if (
                    figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
                    figure.role == Figure.ROLE.RECOMMENDED and
                    figure.event.crisis == crisis
                )
            ])
            filtered_figures = []
            for figure in self.figures:
                if (
                    figure.category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT and
                    figure.role == Figure.ROLE.RECOMMENDED and
                    figure.event.crisis == crisis
                ):
                    filtered_figures.append(figure)
                elif (
                    figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
                    figure.role == Figure.ROLE.RECOMMENDED and
                    figure.event.crisis == crisis and
                    stock_inside_range(figure.end_date, max_date)
                ):
                    filtered_figures.append(figure)
            disaster_idps = get_figure_value_sum([
                figure.total_figures for figure in filtered_figures
                if (
                    figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
                    figure.event.event_type == Crisis.CRISIS_TYPE.DISASTER
                )
            ])
            disaster_nds = get_figure_value_sum([
                figure.total_figures for figure in filtered_figures
                if (
                    figure.category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT and
                    figure.event.event_type == Crisis.CRISIS_TYPE.DISASTER
                )
            ])
            conflict_idps = get_figure_value_sum([
                figure.total_figures for figure in filtered_figures
                if (
                    figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
                    figure.event.event_type == Crisis.CRISIS_TYPE.CONFLICT
                )
            ])
            conflict_nds = get_figure_value_sum([
                figure.total_figures for figure in filtered_figures
                if (
                    figure.category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT and
                    figure.event.event_type == Crisis.CRISIS_TYPE.CONFLICT
                )
            ])
            crisis_reports.append({
                'name': crisis.name,
                'idps_reference_date': max_date.strftime('%Y-%m-%d'),
                'disaster_idps': disaster_idps,
                'conflict_idps': conflict_idps,
                'disaster_nds': disaster_nds,
                'conflict_nds': conflict_nds,
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
        assert crisis_reports == system_data

    def test_report_data(self):
        # Excepted grid Reports
        reports = []
        for year in [2010, 2011, 2012, 2013]:
            for country in [self.country_npl, self.country_ind, None]:
                filtered_figures = []
                for figure in self.figures:
                    if (
                        figure.category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT and
                        figure.role == Figure.ROLE.RECOMMENDED and
                        flow_inside_range(
                            figure.start_date,
                            figure.end_date,
                            date(year, 1, 1),
                            date(year, 12, 31),
                        ) and (
                            not country or
                            figure.country == country
                        )
                    ):
                        filtered_figures.append(figure)
                    elif (
                        figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
                        figure.role == Figure.ROLE.RECOMMENDED and
                        stock_inside_range(
                            figure.end_date,
                            date(year, 12, 31),
                        ) and (
                            not country or
                            figure.country == country
                        )
                    ):
                        filtered_figures.append(figure)
                disaster_idps = get_figure_value_sum([
                    figure.total_figures for figure in filtered_figures
                    if (
                        figure.event.event_type == Crisis.CRISIS_TYPE.DISASTER and
                        figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS
                    )
                ])
                disaster_nds = get_figure_value_sum([
                    figure.total_figures for figure in filtered_figures
                    if (
                        figure.event.event_type == Crisis.CRISIS_TYPE.DISASTER and
                        figure.category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT
                    )
                ])
                conflict_idps = get_figure_value_sum([
                    figure.total_figures for figure in filtered_figures
                    if (
                        figure.event.event_type == Crisis.CRISIS_TYPE.CONFLICT and
                        figure.category == Figure.FIGURE_CATEGORY_TYPES.IDPS
                    )
                ])
                conflict_nds = get_figure_value_sum([
                    figure.total_figures for figure in filtered_figures
                    if (
                        figure.event.event_type == Crisis.CRISIS_TYPE.CONFLICT and
                        figure.category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT
                    )
                ])
                report_name = (
                    f'GRID {year + 1}' if country is None else
                    f'GRID {year + 1} - {country.iso3}'
                )
                start_date, end_date = (
                    date(year=year, month=1, day=1),
                    date(year=year + 1, month=1, day=1) - timedelta(days=1),
                )
                reports.append({
                    'name': report_name,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'disaster_idps': disaster_idps,
                    'conflict_idps': conflict_idps,
                    'disaster_nds': disaster_nds,
                    'conflict_nds': conflict_nds,
                })
                # Create a report in the helix as well
                system_report = ReportFactory.create(
                    name=report_name,
                    filter_figure_start_after=start_date,
                    filter_figure_end_before=end_date,
                    is_public=True,
                )
                if country:
                    system_report.filter_figure_countries.set([country])

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
        assert reports == system_data
