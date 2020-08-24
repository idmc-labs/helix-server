from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationAbstractModel


class Crisis(MetaInformationAbstractModel, models.Model):
    class CRISIS_TYPE(enum.Enum):
        CONFLICT = 0
        DISASTER = 1

    name = models.CharField(verbose_name=_('Name'), max_length=256)
    crisis_type = enum.EnumField(CRISIS_TYPE, verbose_name=_('Crisis Type'))
    crisis_narrative = models.TextField(_('Crisis Narrative/Summary'))
    countries = models.ManyToManyField('country.Country', verbose_name=_('Countries'),
                                       related_name='crises')

    def __str__(self):
        return self.name
