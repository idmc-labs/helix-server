"""`Sources` and `Sources type` are positionally paired, and one of them can carry gaps.

The two columns are separate `ArrayAgg`s over one shared `ordering`, so the only thing tying a
kind to its organisation is the slot it sits in. `organization_kind` is nullable, so a source
without one leaves a NULL in `sources_type` while `sources` stays full-length. Joining with
`string_join` drops that NULL and pulls every later kind one slot left, attributing it to the
wrong source in a cell that still looks well-formed.
"""

import io

import openpyxl
from django.test import TestCase

from apps.common.utils import EXTERNAL_ARRAY_SEPARATOR
from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.gidd.models import GiddFigure, PublicFigureAnalysis, StatusLog
from apps.gidd.tasks import update_gidd_data
from apps.gidd.views import DisaggregationViewSet
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
    OrganizationFactory,
    OrganizationKindFactory,
    ReportFactory,
)
from utils.tests import create_user_with_role


class GiddExportSourceTypeTestCase(TestCase):
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

    def figure_with_sources(self):
        figure = FigureFactory.create(
            entry=EntryFactory.create(publish_date="2019-01-01", is_confidential=False),
            event=self.event,
            country=self.country,
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            total_figures=500,
            start_date="2018-01-01",
            end_date="2018-12-31",
        )
        # The FIRST source carries no kind, so a dropped slot shows as the second source's kind
        # moving to the front rather than only as a length change.
        for name, kind in (("Alpha Agency", None), ("Beta Bureau", "Media")):
            figure.sources.add(
                OrganizationFactory.create(
                    name=name,
                    organization_kind=None if kind is None else OrganizationKindFactory.create(name=kind),
                )
            )
        return figure

    def export_row(self):
        workbook = DisaggregationViewSet()._export_disaggregated_excel(
            "probe.xlsx", GiddFigure.objects.all(), PublicFigureAnalysis.objects.none()
        )
        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        rows = list(openpyxl.load_workbook(buffer, read_only=True)["1_Disaggregated_Data"].values)
        return {name: index for index, name in enumerate(rows[0])}, rows[1]

    def test_generation_keeps_a_null_slot_for_a_source_with_no_kind(self):
        gidd_figure = self.generate(self.figure_with_sources())

        assert len(gidd_figure.sources) == 2, gidd_figure.sources
        assert len(gidd_figure.sources_type) == 2, f"sources_type lost a slot: {gidd_figure.sources_type}"
        by_source = dict(zip(gidd_figure.sources, gidd_figure.sources_type))
        assert by_source == {"Alpha Agency": None, "Beta Bureau": "Media"}, by_source

    def test_the_xlsx_keeps_an_empty_slot_for_a_source_with_no_kind(self):
        self.generate(self.figure_with_sources())
        position, row = self.export_row()

        sources = (row[position["Sources"]] or "").split(EXTERNAL_ARRAY_SEPARATOR)
        types = (row[position["Sources type"]] or "").split(EXTERNAL_ARRAY_SEPARATOR)
        assert len(types) == len(sources), f"{len(types)} kind slots against {len(sources)} sources"
        assert types[sources.index("Alpha Agency")] == "", f"the empty slot was dropped: {types}"
        assert types[sources.index("Beta Bureau")] == "Media", f"the kind moved slot: {types}"
