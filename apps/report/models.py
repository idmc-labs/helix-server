from datetime import datetime
import logging

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Sum, Q, F, Exists
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationArchiveAbstractModel
from apps.crisis.models import Crisis
from apps.entry.constants import STOCK, FLOW
from apps.entry.models import FigureDisaggregationAbstractModel, Figure
from apps.extraction.models import QueryAbstractModel
# from utils.permissions import cache_me
from utils.fields import CachedFileField

logger = logging.getLogger(__name__)
User = get_user_model()


class Report(MetaInformationArchiveAbstractModel,
             QueryAbstractModel,
             FigureDisaggregationAbstractModel,
             models.Model):
    class REPORT_TYPE(enum.Enum):
        GROUP = 0
        MASTERFACT = 1

    TOTAL_FIGURE_DISAGGREGATIONS = dict(
        total_stock_conflict=Sum(
            'total_figures',
            filter=Q(category__type=STOCK,
                     role=Figure.ROLE.RECOMMENDED,
                     entry__event__event_type=Crisis.CRISIS_TYPE.CONFLICT)
        ),
        total_flow_conflict=Sum(
            'total_figures',
            filter=Q(category__type=FLOW,
                     role=Figure.ROLE.RECOMMENDED,
                     entry__event__event_type=Crisis.CRISIS_TYPE.CONFLICT)
        ),
        total_stock_disaster=Sum(
            'total_figures',
            filter=Q(category__type=STOCK,
                     role=Figure.ROLE.RECOMMENDED,
                     entry__event__event_type=Crisis.CRISIS_TYPE.DISASTER)
        ),
        total_flow_disaster=Sum(
            'total_figures',
            filter=Q(category__type=FLOW,
                     role=Figure.ROLE.RECOMMENDED,
                     entry__event__event_type=Crisis.CRISIS_TYPE.DISASTER)
        ),
    )

    generated_from = enum.EnumField(REPORT_TYPE,
                                    blank=True, null=True, editable=False)
    # TODO: Remove me after next migration run
    generated = models.BooleanField(verbose_name=_('Generated'), default=True,
                                    editable=False)
    reports = models.ManyToManyField('self', verbose_name=_('Reports (old groups)'),
                                     blank=True, related_name='masterfact_reports',
                                     symmetrical=False)
    # Do not access me, instead access report_figures property
    figures = models.ManyToManyField('entry.Figure',
                                     blank=True)
    # query fields but modified
    figure_start_after = models.DateField(verbose_name=_('From Date'), null=True)
    figure_end_before = models.DateField(verbose_name=_('To Date'), null=True)
    # user entered fields
    analysis = models.TextField(verbose_name=_('Analysis'),
                                blank=True, null=True)
    methodology = models.TextField(verbose_name=_('Methodology'), blank=True, null=True)
    significant_updates = models.TextField(verbose_name=_('Significant Updates'),
                                           blank=True, null=True)
    challenges = models.TextField(verbose_name=_('Challenges'), blank=True, null=True)

    reported = models.PositiveIntegerField(verbose_name=_('Reported Figures'), default=0, editable=False)
    total_figures = models.PositiveIntegerField(verbose_name=_('Total Figures'), default=0,
                                                editable=False)
    # old fields will be migrated into summary
    summary = models.TextField(verbose_name=_('Summary'), blank=True, null=True,
                               help_text=_('It will store master fact information:'
                                           'Comment, Source Excerpt, IDU Excerpt, Breakdown & '
                                           'Reliability, and Caveats'))
    is_signed_off = models.BooleanField(default=False)
    approvers = models.ManyToManyField(User, verbose_name=_('Approvers'),
                                       through='ReportApproval',
                                       through_fields=('report', 'created_by'),
                                       related_name='approved_reports')

    @property
    def report_figures(self):
        # TODO: use generated_from after next migration
        if not self.generated:
            figures_ids = (Report.objects.filter(id=self.id) |
                           Report.objects.get(id=self.id).masterfact_reports.all()).values('figures')
        else:
            figures_ids = self.extract_figures
        return Figure.objects.filter(id__in=figures_ids)

    @property
    # @cache_me(3000)
    def countries_report(self) -> list:
        return self.report_figures.select_related(
            'country'
        ).values('country').order_by().distinct().annotate(
            # id is needed by apollo-client
            id=F('country_id'),
            **self.TOTAL_FIGURE_DISAGGREGATIONS,
        )

    @property
    # @cache_me(3000)
    def events_report(self) -> list:
        return self.report_figures.select_related(
            'entry__event'
        ).prefetch_related(
            'entry__event__countries'
        ).values('entry__event').order_by().distinct().annotate(
            # id is needed by apollo-client
            id=F('entry__event_id'),
            **self.TOTAL_FIGURE_DISAGGREGATIONS,
        )

    @property
    # @cache_me(3000)
    def entries_report(self) -> list:
        from apps.entry.filters import reviewed_subquery, signed_off_subquery

        return self.report_figures.select_related(
            'entry'
        ).values('entry').order_by().distinct().annotate(
            # id is needed by apollo-client
            id=F('entry_id'),
            is_reviewed=Exists(reviewed_subquery),
            is_signed_off=Exists(signed_off_subquery),
            **self.TOTAL_FIGURE_DISAGGREGATIONS,
        )

    @property
    # @cache_me(3000)
    def crises_report(self) -> list:
        return self.report_figures.filter(
            entry__event__crisis__isnull=False
        ).select_related(
            'entry__event__crisis'
        ).values('entry__event__crisis').order_by().distinct().annotate(
            # id is needed by apollo-client
            id=F('entry__event__crisis_id'),
            name=F('entry__event__crisis__name'),
            crisis_type=F('entry__event__crisis__crisis_type'),
            **self.TOTAL_FIGURE_DISAGGREGATIONS,
        )

    @property
    # @cache_me(3000)
    def total_disaggregation(self) -> dict:
        return self.report_figures.annotate(
            **self.TOTAL_FIGURE_DISAGGREGATIONS,
        ).aggregate(
            total_stock_conflict_sum=Sum('total_stock_conflict'),
            total_flow_conflict_sum=Sum('total_flow_conflict'),
            total_stock_disaster_sum=Sum('total_stock_disaster'),
            total_flow_disaster_sum=Sum('total_flow_disaster'),
        )

    # methods

    def sign_off(self, done_by: 'User'):
        self.is_signed_off = True
        self.save()
        ReportSignOff.objects.create(
            report=self,
            created_by=done_by,
            created_at=datetime.now(),
        )

    class Meta:
        # TODO: implement the side effects of report sign off
        permissions = (
            ('sign_off_report', 'Can sign off the report'),
            ('approve_report', 'Can approve the report'),
        )

    def __str__(self):
        return self.name


class ReportComment(MetaInformationArchiveAbstractModel, models.Model):
    body = models.TextField(verbose_name=_('Body'))
    report = models.ForeignKey('Report', verbose_name=_('Report'),
                               related_name='comments', on_delete=models.CASCADE)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.body and self.body[:50]}'


class ReportApproval(MetaInformationArchiveAbstractModel, models.Model):
    report = models.ForeignKey('Report', verbose_name=_('Report'),
                               related_name='approvals', on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, verbose_name=_('Approved By'),
                                   related_name='approvals', on_delete=models.CASCADE)
    is_approved = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.report} {not self.is_approved and "dis"}approved by {self.created_by}'


class ReportSignOff(MetaInformationArchiveAbstractModel, models.Model):
    FULL_REPORT_FOLDER = 'reports/full'
    SNAPSHOT_REPORT_FOLDER = 'reports/snaps'
    report = models.ForeignKey('Report', verbose_name=_('Report'),
                               related_name='sign_offs', on_delete=models.CASCADE)
    # TODO schedule a task on create to generate following files
    full_report = CachedFileField(verbose_name=_('full report'),
                                  blank=True, null=True,
                                  upload_to=FULL_REPORT_FOLDER)
    snapshot = CachedFileField(verbose_name=_('report snapshot'),
                               blank=True, null=True,
                               upload_to=SNAPSHOT_REPORT_FOLDER)

    def __str__(self):
        return f'{self.created_by} signed off {self.report} on {self.created_at}'
