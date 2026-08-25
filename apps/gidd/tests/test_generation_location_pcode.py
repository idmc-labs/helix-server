from django.test import TestCase

from apps.crisis.models import Crisis
from apps.entry.models import Figure, FigureLocation
from apps.gidd.models import GiddFigure, StatusLog
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
    FigureLocationFactory,
    ReportFactory,
)
from utils.tests import create_user_with_role


class GiddFigureLocationPcodeTestCase(TestCase):
    """The pcode arrays have to line up index-for-index with the other location arrays.

    They are five separate `ArrayAgg`s over one `ordering`, so a pcode is only attached to its
    location by position. A mismatched ordering still produces arrays of the right length, which is
    why the fixture gives each location a pcode that names it: a swap is then visible in the values
    rather than only in the lengths.

    One location deliberately carries no pcode. `array_agg` keeps the NULL, so the slot survives and
    the arrays stay aligned; dropping it instead would silently shift every later pcode by one.
    """

    def setUp(self) -> None:
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.country = CountryFactory(name="Nepal", iso3="NPL")
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

    def generate(self, figure):
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
        assert status_log.status == StatusLog.Status.SUCCESS, "generation did not succeed"
        return GiddFigure.objects.get(figure_raw_id=figure.id)

    def test_each_pcode_stays_with_its_location(self):
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
        # Names out of alphabetical order on purpose: the arrays are ordered by the shared
        # `locations_order`, so a name-sorted result would be a different ordering than the pcodes'.
        for name, pcode, accuracy, source in (
            ("Zone-B", "NPL-B", FigureLocation.PCODE_ACCURACY.ADM2, "HDX"),
            ("Alpha-A", "NPL-A", FigureLocation.PCODE_ACCURACY.ADM1, "OCHA"),
            ("Mid-C", None, None, None),
        ):
            figure.geo_locations.add(
                FigureLocationFactory.create(display_name=name, pcode=pcode, pcode_accuracy=accuracy, pcode_source=source)
            )

        gidd_figure = self.generate(figure)

        assert len(gidd_figure.locations_names) == 3, gidd_figure.locations_names
        for field in ("locations_pcode", "locations_pcode_accuracy", "locations_pcode_source"):
            assert len(getattr(gidd_figure, field)) == 3, f"{field} lost a slot: {getattr(gidd_figure, field)}"

        by_name = dict(zip(gidd_figure.locations_names, gidd_figure.locations_pcode))
        assert by_name == {"Zone-B": "NPL-B", "Alpha-A": "NPL-A", "Mid-C": None}, by_name

        sources = dict(zip(gidd_figure.locations_names, gidd_figure.locations_pcode_source))
        assert sources == {"Zone-B": "HDX", "Alpha-A": "OCHA", "Mid-C": None}, sources

        accuracies = dict(zip(gidd_figure.locations_names, gidd_figure.locations_pcode_accuracy))
        assert accuracies == {
            "Zone-B": FigureLocation.PCODE_ACCURACY.ADM2.value,
            "Alpha-A": FigureLocation.PCODE_ACCURACY.ADM1.value,
            "Mid-C": None,
        }, accuracies

    def test_a_figure_with_no_locations_publishes_empty_arrays(self):
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
        gidd_figure = self.generate(figure)
        assert gidd_figure.locations_pcode == []
        assert gidd_figure.locations_pcode_accuracy == []
        assert gidd_figure.locations_pcode_source == []
