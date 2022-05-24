from datetime import datetime, timedelta

from django.db import IntegrityError
from django.db import models

from apps.report.models import (
    Report,
    ReportGeneration,
    ReportApproval,
)
from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.users.enums import USER_ROLE
from utils.tests import HelixTestCase, create_user_with_role
from utils.factories import (
    FigureFactory,
    EntryFactory,
    CountryFactory,
    ReportFactory,
    EventFactory,
)


class TestReportModel(HelixTestCase):
    def setUp(self) -> None:
        self.event_conflict = EventFactory.create(event_type=Crisis.CRISIS_TYPE.CONFLICT)
        self.event_disaster = EventFactory.create(event_type=Crisis.CRISIS_TYPE.DISASTER)

    def test_002_appropriate_figures_are_summed_up(self):
        c = CountryFactory.create()
        # we are checking if the methods considers figures beyond the given dates during aggregation
        entry = EntryFactory.create()
        f1 = FigureFactory.create(entry=entry,
                                  country=c,
                                  reported=100,
                                  role=Figure.ROLE.RECOMMENDED,
                                  unit=Figure.UNIT.PERSON,
                                  start_date=datetime.today(),
                                  end_date=datetime.today() + timedelta(days=3),
                                  event=self.event_conflict,
                                  )
        f1.category = Figure.FIGURE_CATEGORY_TYPES.IDPS
        f1.save()
        f2 = FigureFactory.create(entry=entry,
                                  country=c,
                                  role=Figure.ROLE.RECOMMENDED,
                                  reported=55,
                                  unit=Figure.UNIT.PERSON,
                                  start_date=f1.start_date + timedelta(days=10),
                                  end_date=f1.start_date + timedelta(days=16),
                                  event=self.event_disaster,
                                  )
        f2.category = Figure.FIGURE_CATEGORY_TYPES.IDPS
        f2.save()
        r = Report(filter_figure_start_after=f1.start_date,
                   filter_figure_end_before=f1.end_date - timedelta(days=1))
        r.save()
        assert r.report_figures.count() == 1
        self.assertEqual(r.countries_report[0].total_stock_conflict,
                         f1.total_figures,
                         r.countries_report)

    def test_001_appropriate_typology_checks(self):
        figure = FigureFactory.create(
            reported=200,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            role=Figure.ROLE.RECOMMENDED,
            country=CountryFactory.create(),
            disaggregation_conflict=100,
            disaggregation_conflict_political=100,
            event=self.event_conflict,
        )
        report = ReportFactory.create(generated=False)
        report.figures.add(figure)
        gen = ReportGeneration.objects.create(report=report)

        assert report.report_figures.count() == 1

        filtered_report_figures = report.report_figures.filter(
            role=Figure.ROLE.RECOMMENDED,
            event__event_type=Crisis.CRISIS_TYPE.CONFLICT,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
        ).values('country').order_by()

        data = filtered_report_figures.filter(disaggregation_conflict__gt=0).annotate(
            name=models.F('country__name'),
            iso3=models.F('country__iso3'),
            total=models.Sum('disaggregation_conflict', filter=models.Q(disaggregation_conflict__gt=0)),
            typology=models.Value('Armed Conflict', output_field=models.CharField())
        ).values('name', 'iso3', 'total', 'typology').union(
            filtered_report_figures.filter(disaggregation_conflict_political__gt=0).annotate(
                name=models.F('country__name'),
                iso3=models.F('country__iso3'),
                total=models.Sum('disaggregation_conflict_political',
                                 filter=models.Q(disaggregation_conflict_political__gt=0)),
                typology=models.Value('Violence - Political', output_field=models.CharField())
            ).values('name', 'iso3', 'total', 'typology'),
            filtered_report_figures.filter(disaggregation_conflict_criminal__gt=0).annotate(
                name=models.F('country__name'),
                iso3=models.F('country__iso3'),
                total=models.Sum('disaggregation_conflict_criminal',
                                 filter=models.Q(disaggregation_conflict_criminal__gt=0)),
                typology=models.Value('Violence - Criminal', output_field=models.CharField())
            ).values('name', 'iso3', 'total', 'typology'),
            filtered_report_figures.filter(disaggregation_conflict_communal__gt=0).annotate(
                name=models.F('country__name'),
                iso3=models.F('country__iso3'),
                total=models.Sum('disaggregation_conflict_communal',
                                 filter=models.Q(disaggregation_conflict_communal__gt=0)),
                typology=models.Value('Violence - Communal', output_field=models.CharField())
            ).values('name', 'iso3', 'total', 'typology'),
            filtered_report_figures.filter(disaggregation_conflict_other__gt=0).annotate(
                name=models.F('country__name'),
                iso3=models.F('country__iso3'),
                total=models.Sum('disaggregation_conflict_other', filter=models.Q(disaggregation_conflict_other__gt=0)),
                typology=models.Value('Other', output_field=models.CharField())
            ).values('name', 'iso3', 'total', 'typology')
        ).values('name', 'iso3', 'typology', 'total').order_by('typology')
        assert len(data) == 2
        assert len(gen.stat_conflict_typology['data']) == 2, gen.stat_conflict_typology['data']


class TestReportGenerationApproval(HelixTestCase):
    def setUp(self) -> None:
        pass

    def test_report_generation_approval_is_created_only_once(self):
        r = ReportFactory.create()
        gen = ReportGeneration(report=r)
        gen.save()
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
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
