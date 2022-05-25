from collections import OrderedDict
from functools import cached_property
import logging
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models import (
    Sum,
    Q,
    Exists,
    OuterRef,
    Value,
)
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django_enumfield import enum

from apps.contrib.models import MetaInformationArchiveAbstractModel
from apps.country.models import (
    Country,
)
from apps.crisis.models import Crisis
from apps.entry.models import (
    FigureDisaggregationAbstractModel,
    Figure,
    Entry,
)
from apps.event.models import Event
from apps.extraction.models import QueryAbstractModel
from apps.report.tasks import trigger_report_generation
from utils.fields import CachedFileField
from apps.report.utils import (
    report_global_numbers,
    report_stat_flow_country,
    report_stat_flow_region,
    report_stat_conflict_country,
    report_stat_conflict_region,
    report_stat_conflict_typology,
    report_disaster_event,
    report_disaster_country,
    report_disaster_region,
)


logger = logging.getLogger(__name__)
User = get_user_model()

EXCEL_FORMULAE = {
    'per_100k': '=IF({key2}{{row}} <> "", (100000 * {key1}{{row}})/{key2}{{row}}, "")',
    'percent_variation': '=IF({key2}{{row}}, 100 * ({key1}{{row}} - {key2}{{row}})/{key2}{{row}}, "")',
}


class Report(MetaInformationArchiveAbstractModel,
             QueryAbstractModel,
             FigureDisaggregationAbstractModel,
             models.Model):
    class REPORT_TYPE(enum.Enum):
        GROUP = 0
        MASTERFACT = 1

    class REPORT_REVIEW_FILTER(enum.Enum):
        '''Simply for the filtering'''
        SIGNED_OFF = 0
        APPROVED = 1
        UNAPPROVED = 2

        __labels__ = {
            SIGNED_OFF: _("Signed Off"),
            APPROVED: _("Approved"),
            UNAPPROVED: _("Unapproved"),
        }

    @cached_property
    def TOTAL_FIGURE_DISAGGREGATIONS(self):
        return dict(
            total_stock_conflict=Sum(
                'total_figures',
                filter=Q(
                    Q(
                        end_date__isnull=True,
                    ) | Q(
                        end_date__isnull=False,
                        end_date__gte=self.filter_figure_end_before or timezone.now().date(),
                    ),
                    category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
                    role=Figure.ROLE.RECOMMENDED,
                    event__event_type=Crisis.CRISIS_TYPE.CONFLICT,
                )
            ),
            total_flow_conflict=Sum(
                'total_figures',
                filter=Q(category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                         role=Figure.ROLE.RECOMMENDED,
                         event__event_type=Crisis.CRISIS_TYPE.CONFLICT)
            ),
            total_flow_disaster=Sum(
                'total_figures',
                filter=Q(category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                         role=Figure.ROLE.RECOMMENDED,
                         event__event_type=Crisis.CRISIS_TYPE.DISASTER)
            ),
            total_stock_disaster=Sum(
                'total_figures',
                filter=Q(
                    Q(
                        end_date__isnull=True,
                    ) | Q(
                        end_date__isnull=False,
                        end_date__gte=self.filter_figure_end_before or timezone.now().date(),
                    ),
                    category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
                    role=Figure.ROLE.RECOMMENDED,
                    event__event_type=Crisis.CRISIS_TYPE.DISASTER,
                )
            )
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
    filter_figure_start_after = models.DateField(verbose_name=_('From Date'), null=True)
    filter_figure_end_before = models.DateField(verbose_name=_('To Date'), null=True)
    # user entered fields
    analysis = models.TextField(verbose_name=_('Analysis'),
                                blank=True, null=True)
    methodology = models.TextField(verbose_name=_('Methodology'), blank=True, null=True)
    significant_updates = models.TextField(verbose_name=_('Significant Updates'),
                                           blank=True, null=True)
    challenges = models.TextField(verbose_name=_('Challenges'), blank=True, null=True)

    # TODO: remove reported?
    reported = models.PositiveIntegerField(verbose_name=_('Reported Figures'), default=0, editable=False)
    total_figures = models.PositiveIntegerField(verbose_name=_('Total Figures'), default=0,
                                                editable=False)
    # old fields will be migrated into summary
    summary = models.TextField(verbose_name=_('Summary'), blank=True, null=True,
                               help_text=_('It will store master fact information:'
                                           'Comment, Source Excerpt, IDU Excerpt, Breakdown & '
                                           'Reliability, and Caveats'))
    is_signed_off = models.BooleanField(default=False)
    is_signed_off_by = models.ForeignKey(User, verbose_name=_('Last signed off by'),
                                         blank=True, null=True,
                                         related_name='signed_off_reports', on_delete=models.CASCADE)
    is_public = models.BooleanField(default=False)

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.report.filters import ReportFilter

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            old_id='Old Id',
            id='Id',
            created_at='Created At',
            created_by__full_name='Created By',
            name='Name',
            filter_figure_start_after='Start Date',
            filter_figure_end_before='End Date',
            filter_figure_categories="Figure Category",
            total_figures='Masterfact Figures',
            # these are calculated in transformer ref: heavy
            total_flow_conflict_sum='ND Conflict',
            total_flow_disaster_sum='ND Disaster',
            total_stock_conflict_sum='IDPs Conflict',
            total_stock_disaster_sum='IDPs Disaster',

            analysis='Analysis',
            methodology='Methodology',
            significant_updates='Significant Updates',
            challenges='Challenges',
            summary='Summary',
        )
        data = ReportFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.annotate(
            # placeholder
            total_flow_conflict_sum=Value(0, output_field=models.IntegerField()),
            total_flow_disaster_sum=Value(0, output_field=models.IntegerField()),
            total_stock_conflict_sum=Value(0, output_field=models.IntegerField()),
            total_stock_disaster_sum=Value(0, output_field=models.IntegerField()),
        ).order_by('-created_at').select_related(
            'created_by',
        ).prefetch_related(
            'filter_figure_categories',
        )

        def transform_filter_figure_category(figure_categories):
            if figure_categories:
                return '; '.join([category.name if category else "" for category in figure_categories])
            return ''

        def transformer(datum):
            return {
                **datum,
                # ref: heavy
                # NOTE: there must be a better way
                **Report.objects.get(id=datum['id']).total_disaggregation,
                'filter_figure_categories': transform_filter_figure_category(datum['filter_figure_categories'])
            }

        return {
            'headers': headers,
            'data': data.values(*[header for header in headers.keys()]),
            'formulae': None,
            'transformer': transformer,
        }

    @property
    def is_legacy(self):
        # TODO: use generated_from after next migration
        return self.generated_from or not self.generated

    # FIXME: we need to use dataloader
    @property
    def attached_figures(self):
        figures_ids = (Report.objects.filter(id=self.id) |
                       Report.objects.get(id=self.id).masterfact_reports.all()).values('figures')
        return Figure.objects.filter(id__in=figures_ids)

    @property
    def report_figures(self):
        if self.is_legacy:
            return self.attached_figures
        return self.extract_report_figures

    @property
    def countries_report(self) -> list:
        result = Country.objects.filter(
            id__in=self.report_figures.values(
                'country'
            )
        ).annotate(
            **Country._total_figure_disaggregation_subquery(
                self.report_figures,
                ignore_dates=True,
            )
        )
        return result

    @property
    def events_report(self) -> list:
        return Event.objects.filter(
            id__in=self.report_figures.values(
                'event'
            )
        ).annotate(
            **Event._total_figure_disaggregation_subquery(self.report_figures),
        )

    @property
    def entries_report(self) -> list:
        return Entry.objects.filter(
            id__in=self.report_figures.values(
                'entry'
            )
        ).annotate(
            **Entry._total_figure_disaggregation_subquery(self.report_figures),
        )

    @property
    def crises_report(self) -> list:
        return Crisis.objects.filter(
            id__in=self.report_figures.values(
                'event__crisis'
            )
        ).annotate(
            **Crisis._total_figure_disaggregation_subquery(self.report_figures),
        )

    @property
    def total_disaggregation(self) -> dict:
        return self.report_figures.annotate(
            **self.TOTAL_FIGURE_DISAGGREGATIONS,
        ).aggregate(
            total_stock_conflict_sum=Sum('total_stock_conflict'),
            total_flow_conflict_sum=Sum('total_flow_conflict'),
            total_flow_disaster_sum=Sum('total_flow_disaster'),
            total_stock_disaster_sum=Sum('total_stock_disaster')
        )

    @cached_property
    def is_approved(self):
        if self.last_generation:
            return self.last_generation.is_approved
        return None

    @cached_property
    def approvals(self):
        if self.last_generation:
            return self.last_generation.approvals.all()
        return ReportApproval.objects.none()

    @cached_property
    def active_generation(self):
        # NOTE: There should be at most one active generation
        return self.generations.filter(is_signed_off=False).first()

    @cached_property
    def last_generation(self):
        return self.generations.annotate(
            is_approved=Exists(ReportApproval.objects.filter(
                generation=OuterRef('pk'),
                is_approved=True,
            ))
        ).order_by('-created_at').first()

    def sign_off(self, done_by: 'User', include_history: bool = False):
        current_gen = ReportGeneration.objects.get(
            report=self,
            is_signed_off=False,
        )
        current_gen.include_history = include_history
        current_gen.is_signed_off = True
        current_gen.is_signed_off_by = done_by
        current_gen.is_signed_off_on = timezone.now()
        current_gen.created_at = timezone.now()
        current_gen.created_by = done_by
        current_gen.save(
            update_fields=[
                'is_signed_off', 'is_signed_off_by',
                'is_signed_off_on', 'include_history',
            ]
        )
        transaction.on_commit(lambda: trigger_report_generation.delay(
            current_gen.pk
        ))

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
        return self.body and self.body[:50]


class ReportApproval(MetaInformationArchiveAbstractModel, models.Model):
    generation = models.ForeignKey('ReportGeneration', verbose_name=_('Report'),
                                   related_name='approvals', on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, verbose_name=_('Approved By'),
                                   related_name='approvals', on_delete=models.CASCADE)
    is_approved = models.BooleanField(default=True)

    class Meta:
        unique_together = (('generation', 'created_by'),)

    def __str__(self):
        return f'{self.generation.report} {"approved" if self.is_approved else "disapproved"} by {self.created_by}'


def full_report_upload_to(instance, filename: str) -> str:
    return f'generation/full/{uuid4()}/{filename}'


def snapshot_report_upload_to(instance, filename: str) -> str:
    return f'generation/snapshot/{uuid4()}/{filename}'


class ReportGeneration(MetaInformationArchiveAbstractModel, models.Model):
    '''
    A report can be generated multiple times, each called a generation
    '''
    class REPORT_GENERATION_STATUS(enum.Enum):
        PENDING = 0
        IN_PROGRESS = 1
        COMPLETED = 2
        FAILED = 3
        KILLED = 4

    report = models.ForeignKey('Report', verbose_name=_('Report'),
                               related_name='generations', on_delete=models.CASCADE)
    is_signed_off = models.BooleanField(default=False)
    is_signed_off_on = models.DateTimeField(
        verbose_name=_('Is signed off on'),
        null=True
    )
    is_signed_off_by = models.ForeignKey(User, verbose_name=_('Is Signed Off By'),
                                         blank=True, null=True,
                                         related_name='signed_off_generations', on_delete=models.CASCADE)
    approvers = models.ManyToManyField(User, verbose_name=_('Approvers'),
                                       through='ReportApproval',
                                       through_fields=('generation', 'created_by'),
                                       related_name='approved_generations')
    # TODO schedule a task on create to generate following files
    full_report = CachedFileField(verbose_name=_('full report'),
                                  blank=True, null=True,
                                  upload_to=full_report_upload_to)
    snapshot = CachedFileField(verbose_name=_('report snapshot'),
                               blank=True, null=True,
                               upload_to=snapshot_report_upload_to)
    status = enum.EnumField(
        REPORT_GENERATION_STATUS,
        default=REPORT_GENERATION_STATUS.PENDING,
    )
    started_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
    include_history = models.BooleanField(
        verbose_name=_('Include History'),
        help_text=_('Including history will take good amount of time.'),
        default=False,
    )

    class Meta:
        ordering = ('-created_at',)

    @cached_property
    def is_approved(self):
        return self.approvals.filter(is_approved=True).exists()

    @property
    def stat_flow_country(self):
        return report_stat_flow_country(self.report)

    @cached_property
    def stat_flow_region(self):
        return report_stat_flow_region(self.report)

    @cached_property
    def stat_conflict_country(self):
        return report_stat_conflict_country(self.report, self.include_history)

    @cached_property
    def stat_conflict_region(self):
        return report_stat_conflict_region(self.report, self.include_history)

    @cached_property
    def stat_conflict_typology(self):
        return report_stat_conflict_typology(self.report)

    @cached_property
    def global_numbers(self):
        return report_global_numbers(self.report)

    @cached_property
    def disaster_event(self):
        return report_disaster_event(self.report)

    @cached_property
    def disaster_region(self):
        return report_disaster_region(self.report, self.include_history)

    @cached_property
    def disaster_country(self):
        return report_disaster_country(self.report, self.include_history)

    def get_excel_sheets_data(self):
        '''
        Returns title and corresponding computed property
        '''
        return {
            'Global Numbers': self.global_numbers,
            'ND Country': self.stat_flow_country,
            'ND Region': self.stat_flow_region,
            'Conflict Country': self.stat_conflict_country,
            'Conflict Region': self.stat_conflict_region,
            'Conflict Typology': self.stat_conflict_typology,
            'Disaster Event': self.disaster_event,
            'Disaster Country': self.disaster_country,
            'Disaster Region': self.disaster_region,
        }

    def get_snapshot(self):
        '''
        Create a snapshot of all the relevant data for the report
        '''
        return dict(
            figures=self.report.report_figures.select_related(
                'created_by', 'last_modified_by', 'country', 'category', 'country__region',
            ).values(
                'id', 'old_id', 'created_at', 'modified_at', 'created_by__email',
                'last_modified_by__email', 'disaggregation_displacement_urban',
                'disaggregation_displacement_rural', 'disaggregation_location_camp',
                'disaggregation_location_non_camp', 'disaggregation_sex_male',
                'disaggregation_sex_female', 'disaggregation_lgbtiq', 'disaggregation_disability',
                'disaggregation_indigenous_people',
                'disaggregation_strata_json', 'disaggregation_conflict',
                'disaggregation_conflict_political', 'disaggregation_conflict_criminal',
                'disaggregation_conflict_communal', 'disaggregation_conflict_other',
                'entry', 'was_subfact', 'quantifier', 'reported', 'unit',
                'household_size', 'total_figures', 'term', 'category__name', 'role',
                'start_date', 'end_date', 'include_idu', 'excerpt_idu', 'country__name',
                'country__region__name', 'is_disaggregated', 'is_housing_destruction',
                'source_excerpt', 'calculation_logic', 'caveats'
            ),
            entries=Entry.objects.filter(
                id__in=self.report.report_figures.values('entry')
            ).select_related(
                'created_by', 'last_modified_by'
            ).values(
                'id', 'old_id', 'created_at', 'modified_at', 'created_by__email',
                'last_modified_by__email', 'version_id', 'url',
                'article_title', 'publish_date',
                'event', 'idmc_analysis', 'is_confidential',
            ),
            events=Event.objects.filter(
                id__in=self.report.report_figures.values('event')
            ).select_related(
                'created_by', 'last_modified_by', 'violence',
                'violence_sub_type', 'actor', 'disaster_category', 'disaster_sub_category',
                'disaster_type', 'disaster_sub_type'
            ).values(
                'id', 'old_id', 'created_at', 'modified_at', 'created_by__email',
                'last_modified_by__email', 'crisis', 'name', 'event_type',
                'other_sub_type', 'violence__name',
                'violence_sub_type__name', 'actor__name', 'disaster_category__name',
                'disaster_sub_category__name', 'disaster_type__name', 'disaster_sub_type__name',
                'start_date', 'end_date', 'event_narrative',
            ),
        )

    def __str__(self):
        return f'{self.created_by} signed off {self.report} on {self.created_at}'
