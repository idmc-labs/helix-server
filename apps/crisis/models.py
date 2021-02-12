from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationAbstractModel
from apps.entry.models import Figure


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
    end_date = models.DateField(verbose_name=_('End Date'), blank=True, null=True)

    # property

    @property
    def total_stock_figures(self) -> int:
        filters = dict(crisis=self.id)
        return Figure.get_total_stock_figure(filters)

    @property
    def total_flow_figures(self) -> int:
        filters = dict(crisis=self.id)
        return Figure.get_total_flow_figure(filters)

    # dunders

    def __str__(self):
        return self.name
