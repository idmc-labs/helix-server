from django.test import TestCase

from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.event.models import Event
from apps.gidd.models import (
    GiddEvent,
    GiddFigure,
    StatusLog,
)
from apps.gidd.tasks import update_gidd_data
from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    DisasterCategoryFactory,
    DisasterSubCategoryFactory,
    DisasterSubTypeFactory,
    DisasterTypeFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
    ReportFactory,
)
from utils.tests import create_user_with_role


class GiddTestCase(TestCase):
    def setUp(self) -> None:
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.country = CountryFactory(name="Nepal", iso3="NEP")
        self.event1 = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.CONFLICT, start_date="2008-01-01", end_date="2008-12-31"
        )
        self.event2 = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.DISASTER, start_date="2008-01-01", end_date="2008-12-31"
        )
        self.event3 = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.CONFLICT, start_date="2018-01-01", end_date="2018-12-31"
        )
        self.entry = EntryFactory.create(publish_date="2009-01-01")
        self.entry2 = EntryFactory.create(publish_date="2019-01-01")
        self.hazard_category = DisasterCategoryFactory.create()
        self.hazard_sub_category = DisasterSubCategoryFactory.create()
        self.hazard_type = DisasterTypeFactory.create()
        self.hazard_sub_type = DisasterSubTypeFactory.create()

    def test_gidd_update_pre_2016(self):
        figure_1 = FigureFactory.create(
            entry=self.entry,
            event=self.event1,
            country=self.country,
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            total_figures=100,
            start_date="2008-01-01",
            end_date="2008-12-31",
        )

        figure_2 = FigureFactory.create(
            entry=self.entry,
            event=self.event1,
            country=self.country,
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            total_figures=200,
            start_date="2008-01-01",
            end_date="2008-12-31",
        )
        figure_3 = FigureFactory.create(
            entry=self.entry,
            event=self.event2,
            country=self.country,
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            total_figures=300,
            start_date="2008-01-01",
            end_date="2008-12-31",
        )
        figure_4 = FigureFactory.create(
            entry=self.entry,
            event=self.event2,
            country=self.country,
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            total_figures=400,
            start_date="2008-01-01",
            end_date="2008-12-31",
        )
        figure_5 = FigureFactory.create(
            entry=self.entry2,
            event=self.event3,
            country=self.country,
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            total_figures=500,
            start_date="2018-01-01",
            end_date="2018-12-31",
        )
        figure_6 = FigureFactory.create(
            entry=self.entry2,
            event=self.event3,
            country=self.country,
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            total_figures=600,
            start_date="2018-01-01",
            end_date="2018-12-31",
        )
        # Add report for 2008
        report = ReportFactory.create(is_gidd_report=True, gidd_report_year=2008)
        report.figures.add(figure_1)
        report.figures.add(figure_2)
        report.figures.add(figure_3)
        report.figures.add(figure_4)

        # Add report for 2018
        report2 = ReportFactory.create(is_gidd_report=True, gidd_report_year=2018)
        report2.figures.add(figure_5)
        report2.figures.add(figure_6)

        status_log = StatusLog.objects.create(
            triggered_by=self.user, triggered_at="2018-01-01", completed_at="2018-01-01", status=StatusLog.Status.PENDING
        )

        assert GiddEvent.objects.count() == 0
        assert GiddFigure.objects.count() == 0
        # generate gidd data
        update_gidd_data(status_log.id)

        assert GiddEvent.objects.count() == Event.objects.count()
        assert GiddFigure.objects.count() == Figure.objects.count()

        status_log.refresh_from_db()
        assert status_log.status == StatusLog.Status.SUCCESS
