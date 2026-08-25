from django.test import TestCase

from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.event.models import EventCode
from apps.gidd.models import GiddEvent, GiddEventDisplacement, StatusLog
from apps.gidd.tasks import update_gidd_data
from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    DisasterCategoryFactory,
    DisasterSubCategoryFactory,
    DisasterSubTypeFactory,
    DisasterTypeFactory,
    EntryFactory,
    EventCodeFactory,
    EventFactory,
    FigureFactory,
    ReportFactory,
)
from utils.tests import create_user_with_role


class GiddDuplicateEventCodeTestCase(TestCase):
    """Pins how generation renders two EventCodes that differ only by id.

    The copies are sorted by (event_code, event_code_type, iso3) and no longer deduplicated on it,
    so a duplicate row is published twice where the previous pipeline emitted it once. Nothing in
    the schema prevents the duplicate -- `event_eventcode` carries no constraint over that tuple --
    so the behaviour is pinned here to make a future change deliberate.
    """

    def setUp(self) -> None:
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.country = CountryFactory(name="Nepal", iso3="NEP")
        self.event = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.DISASTER,
            start_date="2018-01-01",
            end_date="2018-12-31",
            disaster_category=DisasterCategoryFactory.create(),
            disaster_sub_category=DisasterSubCategoryFactory.create(),
            disaster_type=DisasterTypeFactory.create(),
            disaster_sub_type=DisasterSubTypeFactory.create(),
        )
        self.event.countries.add(self.country)
        for _ in range(2):
            EventCodeFactory.create(
                event=self.event,
                country=self.country,
                event_code="GLIDE-DUP-1",
                event_code_type=EventCode.EVENT_CODE_TYPE.GLIDE_NUMBER,
            )

    def test_a_duplicate_event_code_is_published_twice(self):
        figure = FigureFactory.create(
            entry=EntryFactory.create(publish_date="2019-01-01"),
            event=self.event,
            country=self.country,
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            total_figures=500,
            start_date="2018-01-01",
            end_date="2018-12-31",
        )
        report = ReportFactory.create(is_gidd_report=True, gidd_report_year=2018)
        report.figures.add(figure)
        status_log = StatusLog.objects.create(
            triggered_by=self.user,
            triggered_at="2018-01-01",
            completed_at="2018-01-01",
            status=StatusLog.Status.PENDING,
        )

        update_gidd_data(status_log.id)

        status_log.refresh_from_db()
        assert status_log.status == StatusLog.Status.SUCCESS

        # One row per (event, country, year) -- the grain the retired Disaster table had.
        disaster = GiddEventDisplacement.objects.get(event_raw_id=self.event.id, country_id=self.country.id, year=2018)
        assert disaster.event_codes == ["GLIDE-DUP-1", "GLIDE-DUP-1"]
        # The two arrays are built by separate aggregates over one sort; a code must keep its label.
        assert len(disaster.event_codes) == len(disaster.event_codes_type)

        gidd_event = GiddEvent.objects.get(id=self.event.id)
        assert gidd_event.event_codes == ["GLIDE-DUP-1", "GLIDE-DUP-1"]
