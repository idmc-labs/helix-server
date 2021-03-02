from datetime import datetime, timedelta

from apps.report.models import Report
from apps.crisis.models import Crisis
from apps.entry.constants import STOCK
from apps.entry.models import Figure
from utils.tests import HelixTestCase
from utils.factories import (
    FigureFactory,
    EntryFactory,
    CountryFactory,
)


class TestReportModel(HelixTestCase):
    def setUp(self) -> None:
        pass

    def test_appropriate_figures_are_summed_up(self):
        c = CountryFactory.create()
        # we are checking if the methods considers figures beyond the given dates during aggregation
        entry = EntryFactory.create()
        entry.event.event_type = Crisis.CRISIS_TYPE.CONFLICT
        entry.event.save()
        f1 = FigureFactory.create(entry=entry,
                                  country=c,
                                  reported=100,
                                  role=Figure.ROLE.RECOMMENDED,
                                  unit=Figure.UNIT.PERSON,
                                  start_date=datetime.today(),
                                  end_date=datetime.today() + timedelta(days=3))
        f1.category.type = STOCK
        f1.category.save()
        f2 = FigureFactory.create(entry=entry,
                                  country=c,
                                  role=Figure.ROLE.RECOMMENDED,
                                  reported=55,
                                  unit=Figure.UNIT.PERSON,
                                  start_date=f1.start_date + timedelta(days=10),
                                  end_date=f1.start_date + timedelta(days=16))
        f2.category.type = STOCK
        f2.category.save()
        r = Report(figure_start_after=f1.start_date,
                   figure_end_before=f1.end_date - timedelta(days=1))
        r.save()
        assert r.report_figures.count() == 1

        self.assertEqual(r.countries_report[0]['total_stock_conflict'],
                         f1.total_figures,
                         r.countries_report)
