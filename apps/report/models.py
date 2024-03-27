from collections import OrderedDict
from functools import cached_property
import logging
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction
from django.db.models import (
    Sum,
    Q,
    Exists,
    OuterRef,
    Value,
    F,
)
from django.db.models.functions import Concat
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django_enumfield import enum
from django.contrib.postgres.aggregates.general import StringAgg

from utils.common import get_string_from_list
from apps.contrib.models import MetaInformationArchiveAbstractModel
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
from apps.common.utils import EXTERNAL_ARRAY_SEPARATOR, EXTERNAL_FIELD_SEPARATOR


logger = logging.getLogger(__name__)
User = get_user_model()

# FIXME: is this used anywhere? We have a duplicate in report/utils
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
                filter=Q(
                    category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                    role=Figure.ROLE.RECOMMENDED,
                    event__event_type=Crisis.CRISIS_TYPE.CONFLICT
                ),
            ),
            total_flow_disaster=Sum(
                'total_figures',
                filter=Q(
                    category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                    role=Figure.ROLE.RECOMMENDED,
                    event__event_type=Crisis.CRISIS_TYPE.DISASTER
                ),
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
            ),
            total_flow=Sum(
                'total_figures',
                filter=Q(
                    category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                    role=Figure.ROLE.RECOMMENDED,
                    event__event_type__in=[Crisis.CRISIS_TYPE.DISASTER, Crisis.CRISIS_TYPE.CONFLICT]
                ),
            ),
            total_stock=Sum(
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
                    event__event_type__in=[Crisis.CRISIS_TYPE.DISASTER, Crisis.CRISIS_TYPE.CONFLICT]
                )
            ),
        )

    name = models.CharField(
        verbose_name=_('Name'),
        max_length=128
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
    public_figure_analysis = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Public figure analysis'),
    )
    is_pfa_visible_in_gidd = models.BooleanField(
        default=False,
        verbose_name=_('Is public figure analysis visible in GIDD'),
    )
    is_gidd_report = models.BooleanField(
        default=False,
        verbose_name=_('Is GIDD report?'),
    )
    gidd_report_year = models.PositiveIntegerField(
        verbose_name=_('GIDD report year'), null=True, unique=True
    )
    gidd_published_date = models.DateTimeField(
        verbose_name=_('Date of data publication into the GIDD'),
        null=True
    )
    is_pfa_published_in_gidd = models.BooleanField(
        verbose_name=_('Is PFA published in GIDD'),
        default=False
    )
    change_in_source = models.BooleanField(default=False)
    change_in_methodology = models.BooleanField(default=False)
    change_in_data_availability = models.BooleanField(default=False)
    retroactive_change = models.BooleanField(default=False)

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.report.filters import ReportFilter

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            old_id='Old ID',
            id='ID',
            created_at='Created at',
            modified_at='Modified at',
            created_by__full_name='Created by',
            name='Name',
            iso3='Iso3',
            public_figure_analysis='Public figure analysis',
            filter_figure_start_after='Start date',
            filter_figure_end_before='End date',
            filter_figure_categories="Figure category",
            total_figures='Masterfact figures',
            # these are calculated in transformer ref: heavy
            total_flow_conflict_sum='ND conflict',
            total_flow_disaster_sum='ND disaster',
            total_stock_conflict_sum='IDPs conflict',
            total_stock_disaster_sum='IDPs disaster',
            analysis='Analysis',
            methodology='Methodology',
            significant_updates='Significant updates',
            challenges='Challenges',
            summary='Summary',
            remarks='Remarks',
            gidd_published_date='Date of data publication in GIDD',
            is_pfa_published_in_gidd='Is public figure analysis published in GIDD'
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
            remarks=Value('', output_field=models.CharField()),
            iso3=StringAgg(
                'filter_figure_countries__iso3', EXTERNAL_ARRAY_SEPARATOR,
                distinct=True, output_field=models.CharField()
            ),
        ).order_by('created_at')

        def transform_filter_figure_category(figure_categories):
            if figure_categories:
                return get_string_from_list([category.label if category else "" for category in figure_categories])
            return ''

        def transformer(datum):
            total_disaggregation = Report.objects.get(id=datum['id']).total_disaggregation
            return {
                **datum,
                # ref: heavy
                # NOTE: there must be a better way
                **total_disaggregation,
                'remarks': Report.objects.get(id=datum['id']).generate_remarks_for_report,
                'filter_figure_categories': transform_filter_figure_category(datum['filter_figure_categories']),

                'is_pfa_published_in_gidd': 'Yes' if datum['is_pfa_published_in_gidd'] else 'No',
            }

        return {
            'headers': headers,
            'data': data.values(*[header for header in headers.keys()]),
            'formulae': None,
            'transformer': transformer,
        }

    @property
    def report_figures(self):
        return self.extract_report_figures

    @property
    def total_disaggregation(self) -> dict:
        return self.report_figures.annotate(
            **self.TOTAL_FIGURE_DISAGGREGATIONS,
        ).aggregate(
            total_stock_conflict_sum=Sum('total_stock_conflict'),
            total_flow_conflict_sum=Sum('total_flow_conflict'),
            total_flow_disaster_sum=Sum('total_flow_disaster'),
            total_stock_disaster_sum=Sum('total_stock_disaster'),
            total_flow_sum=Sum('total_flow'),
            total_stock_sum=Sum('total_stock'),
        )

    @property
    def generate_remarks_for_report(self):
        total_disaggregation = self.total_disaggregation
        total_flow_sum = total_disaggregation['total_flow_sum'] or 0
        total_stock_sum = total_disaggregation['total_stock_sum'] or 0
        figure_categories_to_check = [
            Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value,
            Figure.FIGURE_CATEGORY_TYPES.IDPS.value
        ]
        if self.total_figures in [0, None]:
            return 'The masterfact figure is missing.'

        total_masterfact_figures = self.total_figures or 0
        if (
            self.filter_figure_categories is None or
            (
                bool(
                    set([item.value for item in self.filter_figure_categories]) & set(figure_categories_to_check)
                ) and
                (
                    total_masterfact_figures != total_flow_sum and
                    total_masterfact_figures != total_stock_sum
                )
            )
        ):
            return 'The numbers do no match'
        if not bool(set([item.value for item in self.filter_figure_categories]) & set(figure_categories_to_check)):
            return "The figure category is not 'internal displacement' or 'idps'"
        return ''

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
            ('update_pfa_visibility_report', 'Can update public figure visibility in GIDD'),
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
    return f'report/generation/full/{uuid4()}/{filename}'


def snapshot_report_upload_to(instance, filename: str) -> str:
    return f'report/generation/snapshot/{uuid4()}/{filename}'


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
    full_report = CachedFileField(
        verbose_name=_('full report'),
        blank=True,
        null=True,
        upload_to=full_report_upload_to,
        max_length=256,
    )
    snapshot = CachedFileField(
        verbose_name=_('report snapshot'),
        blank=True,
        null=True,
        upload_to=snapshot_report_upload_to,
        max_length=256,
    )
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
                # Figure model fields
                'id',
                'uuid',
                'entry',
                'was_subfact',
                'quantifier',
                'reported',
                'unit',
                'household_size',
                'total_figures',
                'category',
                'term',
                'displacement_occurred',
                'role',
                'start_date',
                'start_date_accuracy',
                'end_date',
                'end_date_accuracy',
                'include_idu',
                'excerpt_idu',
                'country',
                'is_disaggregated',
                'is_housing_destruction',
                'geo_locations',
                'calculation_logic',
                'tags',
                'source_excerpt',
                'event',
                'context_of_violence',
                'figure_cause',
                'violence',
                'violence_sub_type',
                'disaster_category',
                'disaster_sub_category',
                'disaster_type',
                'disaster_sub_type',
                'other_sub_type',
                'osv_sub_type',
                'sources',
                # Meta information abstract model
                'created_at',
                'modified_at',
                'created_by',
                'last_modified_by',
                'version_id',
                'old_id',
                # UUID abstract fields
                'uuid',
                # Figure disaggregation abstract fields
                'disaggregation_displacement_urban',
                'disaggregation_displacement_rural',
                'disaggregation_location_camp',
                'disaggregation_location_non_camp',
                'disaggregation_lgbtiq',
                'disaggregation_disability',
                'disaggregation_indigenous_people',
                'disaggregation_sex_male',
                'disaggregation_sex_female',
                'disaggregation_age',
                'disaggregation_strata_json',
                'disaggregation_conflict',
                'disaggregation_conflict_political',
                'disaggregation_conflict_criminal',
                'disaggregation_conflict_communal',
                'disaggregation_conflict_other',
            ),
            entries=Entry.objects.filter(
                id__in=self.report.report_figures.values('entry')
            ).select_related(
                'created_by', 'last_modified_by'
            ).values(
                # Entry models
                'id',
                'url',
                'associated_parked_item',
                'preview',
                'document',
                'document_url',
                'article_title',
                'publishers',
                'publish_date',
                'idmc_analysis',
                'is_confidential',
                'reviewers',
                'review_status',
                # Meta information abstract model
                'created_at',
                'modified_at',
                'created_by',
                'last_modified_by',
                'version_id',
                'old_id',
            ),
            events=Event.objects.filter(
                id__in=self.report.report_figures.values('event')
            ).select_related(
                'created_by', 'last_modified_by', 'violence',
                'violence_sub_type', 'actor', 'disaster_category', 'disaster_sub_category',
                'disaster_type', 'disaster_sub_type'
            ).values(
                'id',
                'crisis',
                'name',
                'event_type',
                'other_sub_type',
                'violence',
                'violence_sub_type',
                'actor',
                'disaster_category',
                'disaster_sub_category',
                'disaster_type',
                'disaster_sub_type',
                'countries',
                'start_date',
                'start_date_accuracy',
                'end_date',
                'end_date_accuracy',
                'event_narrative',
                'osv_sub_type',
                'ignore_qa',
                'context_of_violence',
                # Meta information abstract model
                'created_at',
                'modified_at',
                'created_by',
                'last_modified_by',
                'version_id',
                'old_id',
            ).annotate(
                event_codes=models.Func(
                    ArrayAgg(
                        models.Case(
                            models.When(
                                event_code__isnull=False,
                                then=Concat(
                                    F('event_code__event_code'),
                                    Value(EXTERNAL_FIELD_SEPARATOR),
                                    F('event_code__event_code_type'),
                                    Value(EXTERNAL_FIELD_SEPARATOR),
                                    F('event_code__country__iso3'),
                                ),
                            ),
                            output_field=models.CharField(),
                        ),
                    ),
                    None,
                    function='array_remove',
                    output_field=ArrayField(models.CharField()),
                ),
            ),
        )

    def __str__(self):
        return f'{self.created_by} signed off {self.report} on {self.created_at}'
