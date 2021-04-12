from collections import OrderedDict

from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationAbstractModel
from apps.entry.models import Figure
from apps.contrib.commons import DATE_ACCURACY
from apps.users.models import User


class Crisis(MetaInformationAbstractModel, models.Model):
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
            countries='Countries',
        )
        values = CrisisFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.values(*[header for header in headers.keys()])
        data = [
            {
                **datum,
                **dict(
                    start_date_accuracy=getattr(DATE_ACCURACY.get(datum['start_date_accuracy']), 'name', ''),
                    end_date_accuracy=getattr(DATE_ACCURACY.get(datum['end_date_accuracy']), 'name', ''),
                    crisis_type=getattr(Crisis.CRISIS_TYPE.get(datum['event_type']), 'name', ''),
                )
            }
            for datum in values
        ]

        return {
            'headers': headers,
            'data': data,
            'formulae': None,
        }

    # property

    @property
    def total_stock_idp_figures(self) -> int:
        filters = dict(crisis=self.id)
        return Figure.get_total_stock_idp_figure(filters)

    @property
    def total_flow_nd_figures(self) -> int:
        filters = dict(crisis=self.id)
        return Figure.get_total_flow_nd_figure(filters)

    # dunders

    def __str__(self):
        return self.name
