from datetime import datetime, timedelta

from django.db import IntegrityError

from apps.report.models import (
    Report,
    ReportGeneration,
    ReportApproval,
)
from apps.crisis.models import Crisis
from apps.entry.constants import STOCK
from apps.entry.models import Figure
from apps.users.enums import USER_ROLE
from utils.tests import HelixTestCase, create_user_with_role
from utils.factories import (
    FigureFactory,
    EntryFactory,
    CountryFactory,
    ReportFactory,
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
        r = Report(filter_figure_start_after=f1.start_date,
                   filter_figure_end_before=f1.end_date - timedelta(days=1))
        r.save()
        assert r.report_figures.count() == 1

        self.assertEqual(r.countries_report[0]['total_stock_conflict'],
                         f1.total_figures,
                         r.countries_report)


class TestReportGenerationApproval(HelixTestCase):
    def setUp(self) -> None:
        pass

    def test_report_generation_approval_is_created_only_once(self):
        r = ReportFactory.create()
        gen = ReportGeneration(report=r)
        gen.save()
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        ReportApproval.objects.create(
            generation=gen,
            created_by=reviewer,
            is_approved=True
        )
        assert gen.approvers.count() == 1

        try:
            # user disapproves the generation again
            ReportApproval.objects.create(
                generation=gen,
                created_by=reviewer,
                is_approved=False
            )
            assert 1 == 2, 'This should have failed'
        except IntegrityError:
            pass
