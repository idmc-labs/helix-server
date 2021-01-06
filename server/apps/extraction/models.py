from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationAbstractModel
from apps.entry.models import Figure
from apps.extraction.filters import EntryExtractionFilterSet


class ExtractionQuery(MetaInformationAbstractModel):
    regions = models.ManyToManyField('country.CountryRegion', verbose_name=_('Regions'),
                                     blank=True, related_name='+')
    countries = models.ManyToManyField('country.Country', verbose_name=_('Countries'),
                                       blank=True, related_name='+')
    districts = ArrayField(base_field=models.CharField(max_length=256),
                           blank=True, null=True)
    crises = models.ManyToManyField('crisis.Crisis', verbose_name=_('Crises'),
                                    blank=True, related_name='+')
    figure_categories = models.ManyToManyField('entry.FigureCategory',
                                               verbose_name=_('figure categories'),
                                               related_name='+', blank=True)
    event_after = models.DateField(verbose_name=_('From Date'), blank=True, null=True)
    event_before = models.DateField(verbose_name=_('To Date'), blank=True, null=True)
    figure_roles = ArrayField(base_field=enum.EnumField(enum=Figure.ROLE),
                              blank=True, null=True)
    figure_tags = models.ManyToManyField('entry.FigureTag', verbose_name=_('Figure Tags'),
                                         blank=True, related_name='+')

    @classmethod
    def get_entries(cls, data=None) -> ['Entry']:  # noqa
        return EntryExtractionFilterSet(data=data).qs

    @property
    def entries(self) -> ['Entry']:  # noqa
        return self.get_entries(data=dict(
            countries=list(self.countries.all().values_list('id', flat=True)),
            regions=list(self.regions.all().values_list('id', flat=True)),
            crises=list(self.crises.all().values_list('id', flat=True)),
            figure_categories=list(self.figure_categories.all().values_list('id', flat=True)),
            figure_tags=list(self.figure_tags.all().values_list('id', flat=True)),
            districts=self.districts,
            figure_roles=self.figure_roles,
            event_after=self.event_after,
            event_before=self.event_before,
        ))
