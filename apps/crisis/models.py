from collections import OrderedDict

from django.contrib.postgres.aggregates.general import StringAgg
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum
from django.utils import timezone
from django.db.models.functions import Coalesce

from apps.contrib.models import MetaInformationAbstractModel
from apps.contrib.commons import DATE_ACCURACY
from apps.users.models import User


class Crisis(MetaInformationAbstractModel, models.Model):
    # NOTE figure disaggregation variable definitions
    ND_FIGURES_ANNOTATE = 'total_flow_nd_figures'
    IDP_FIGURES_ANNOTATE = 'total_stock_idp_figures'

    class CRISIS_TYPE(enum.Enum):
        CONFLICT = 0
        DISASTER = 1
        OTHER = 2

        __labels__ = {
            CONFLICT: _("Conflict"),
            DISASTER: _("Disaster"),
            OTHER: _("Other"),
        }

    name = models.CharField(verbose_name=_('Name'), max_length=256)
    crisis_type = enum.EnumField(CRISIS_TYPE, verbose_name=_('Cause'))
    crisis_narrative = models.TextField(_('Crisis Narrative/Summary'))
    countries = models.ManyToManyField('country.Country', verbose_name=_('Countries'),
                                       related_name='crises')
    start_date = models.DateField(verbose_name=_('Start Date'), blank=True, null=True)
    start_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_('Start Date Accuracy'),
        default=DATE_ACCURACY.DAY,
        blank=True,
        null=True,
    )
    end_date = models.DateField(verbose_name=_('End Date'), blank=True, null=True)
    end_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_('End date accuracy'),
        default=DATE_ACCURACY.DAY,
        blank=True,
        null=True,
    )

    @classmethod
    def _total_figure_disaggregation_subquery(cls, figures=None):
        from apps.entry.models import Figure
        figures = figures or Figure.objects.all()

        max_stock_end_date_figure_qs = figures.filter(
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            role=Figure.ROLE.RECOMMENDED,
            event__crisis=models.OuterRef('pk'),
        ).order_by('-end_date').values('end_date')[:1]

        return {
            'event_max_end_date': models.Subquery(max_stock_end_date_figure_qs),
            cls.ND_FIGURES_ANNOTATE: models.Subquery(
                Figure.filtered_nd_figures(
                    figures.filter(
                        event__crisis=models.OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                    ),
                    # TODO: what about date range
                    start_date=None,
                    end_date=None,
                ).order_by().values('event__crisis').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
            cls.IDP_FIGURES_ANNOTATE: models.Subquery(
                Figure.filtered_idp_figures(
                    figures.filter(
                        event__crisis=models.OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                    ),
                    start_date=None,
                    end_date=models.OuterRef('event_max_end_date'),
                ).order_by().values('event__crisis').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
        }

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.crisis.filters import CrisisFilter

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            id='ID',
            created_at='Created at',
            created_by__full_name='Created by',
            name='Name',
            start_date='Start date',
            start_date_accuracy='Start date accuracy',
            end_date='End date',
            end_date_accuracy='End date accuracy',
            crisis_type='Cause',
            countries_iso3='ISO3s',
            countries_name='Countries',
            regions_name='Regions',
            events_count='Events count',
            figures_count='Figures count',
            min_event_start='Earliest event start',
            max_event_end='Latest event end',
            **{
                cls.IDP_FIGURES_ANNOTATE: 'IDPs figure',
                cls.ND_FIGURES_ANNOTATE: 'ND figure',
            },
        )
        data = CrisisFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.annotate(
            countries_iso3=StringAgg('countries__iso3', '; ', distinct=True),
            countries_name=StringAgg('countries__idmc_short_name', '; ', distinct=True),
            regions_name=StringAgg('countries__region__name', '; ', distinct=True),
            events_count=models.Count('events', distinct=True),
            min_event_start=models.Min('events__start_date'),
            max_event_end=models.Max('events__end_date'),
            figures_count=models.Count('events__figures', distinct=True),
            **cls._total_figure_disaggregation_subquery(),
        ).order_by('created_at')

        def transformer(datum):
            return {
                **datum,
                **dict(
                    start_date_accuracy=getattr(DATE_ACCURACY.get(datum['start_date_accuracy']), 'name', ''),
                    end_date_accuracy=getattr(DATE_ACCURACY.get(datum['end_date_accuracy']), 'name', ''),
                    crisis_type=getattr(Crisis.CRISIS_TYPE.get(datum['crisis_type']), 'name', ''),
                )
            }

        return {
            'headers': headers,
            'data': data.values(*[header for header in headers.keys()]),
            'formulae': None,
            'transformer': transformer,
        }

    # dunders

    def __str__(self):
        return self.name

    @classmethod
    def annotate_review_figures_count(cls):
        from apps.entry.models import Figure

        return {
            'review_not_started_count': models.Count(
                'events__figures',
                filter=models.Q(
                    events__figures__review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_NOT_STARTED,
                    events__figures__role=Figure.ROLE.RECOMMENDED,
                ) | models.Q(
                    events__figures__review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_NOT_STARTED,
                    events__include_triangulation_in_qa=True,
                )
            ),
            'review_in_progress_count': models.Count(
                'events__figures',
                filter=models.Q(
                    events__figures__review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS,
                    events__figures__role=Figure.ROLE.RECOMMENDED,
                ) | models.Q(
                    events__figures__review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS,
                    events__include_triangulation_in_qa=True,
                )

            ),
            'review_re_request_count': models.Count(
                'events__figures',
                filter=models.Q(
                    events__figures__review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_RE_REQUESTED,
                    events__figures__role=Figure.ROLE.RECOMMENDED,
                ) | models.Q(
                    events__figures__review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_RE_REQUESTED,
                    events__include_triangulation_in_qa=True,
                )

            ),
            'review_approved_count': models.Count(
                'events__figures',
                filter=models.Q(
                    events__figures__review_status=Figure.FIGURE_REVIEW_STATUS.APPROVED,
                    events__figures__role=Figure.ROLE.RECOMMENDED,
                ) | models.Q(
                    events__figures__review_status=Figure.FIGURE_REVIEW_STATUS.APPROVED,
                    events__include_triangulation_in_qa=True,
                )
            ),
            'total_count': (
                models.F('review_not_started_count') +
                models.F('review_in_progress_count') +
                models.F('review_re_request_count') +
                models.F('review_approved_count')
            ),
            'progress': models.Case(
                models.When(
                    total_count__gt=0,
                    then=models.F('review_approved_count') / models.F('total_count')
                ),
                default=models.Value(0),
                output_field=models.FloatField()
            )
        }
