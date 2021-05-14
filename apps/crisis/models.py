from datetime import datetime
from collections import OrderedDict

from django.contrib.postgres.aggregates.general import ArrayAgg
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationAbstractModel
from apps.entry.models import Figure
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
    crisis_type = enum.EnumField(CRISIS_TYPE, verbose_name=_('Crisis Type'))
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
        figures = figures or Figure.objects.all()
        return {
            cls.ND_FIGURES_ANNOTATE: models.Subquery(
                Figure.filtered_nd_figures(
                    figures.filter(
                        entry__event__crisis=models.OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                    ),
                    # TODO: what about date range
                    start_date=datetime(year=datetime.today().year, month=1, day=1),
                    end_date=datetime(year=datetime.today().year, month=12, day=31),
                ).order_by().values('entry__event__crisis').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
            cls.IDP_FIGURES_ANNOTATE: models.Subquery(
                Figure.filtered_idp_figures(
                    figures.filter(
                        entry__event__crisis=models.OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                    )
                ).order_by().values('entry__event__crisis').annotate(
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
            id='Id',
            name='Name',
            start_date='Start Date',
            start_date_accuracy='Start Date Accuracy',
            end_date='End Date',
            end_date_accuracy='End Date Accuracy',
            crisis_type='Crisis Type',
            countries_iso3='ISO3',
            countries_name='Countries',
            regions_name='Regions',
            events_count='Events Count',
            min_event_start='Earliest Event Start',
            max_event_end='Latest Event End',
            figures_count='Figures Count',
            **{
                cls.IDP_FIGURES_ANNOTATE: 'IDPs Figure',
                cls.ND_FIGURES_ANNOTATE: 'ND Figure',
            }
        )
        values = CrisisFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.annotate(
            countries_iso3=ArrayAgg('countries__iso3', distinct=True),
            countries_name=ArrayAgg('countries__name', distinct=True),
            regions_name=ArrayAgg('countries__region__name', distinct=True),
            events_count=models.Count('events', distinct=True),
            min_event_start=models.Min('events__start_date'),
            max_event_end=models.Max('events__end_date'),
            figures_count=models.Count('events__entries__figures', distinct=True),
            **cls._total_figure_disaggregation_subquery(),
        ).order_by('-created_at').select_related(
        ).prefetch_related(
            'countries'
        ).values(*[header for header in headers.keys()])
        data = [
            {
                **datum,
                **dict(
                    start_date_accuracy=getattr(DATE_ACCURACY.get(datum['start_date_accuracy']), 'name', ''),
                    end_date_accuracy=getattr(DATE_ACCURACY.get(datum['end_date_accuracy']), 'name', ''),
                    crisis_type=getattr(Crisis.CRISIS_TYPE.get(datum['crisis_type']), 'name', ''),
                )
            }
            for datum in values
        ]

        return {
            'headers': headers,
            'data': data,
            'formulae': None,
        }

    # dunders

    def __str__(self):
        return self.name
