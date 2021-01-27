from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationAbstractModel
from apps.entry.models import Figure
from apps.crisis.models import Crisis
from apps.extraction.filters import EntryExtractionFilterSet


class QueryAbstractModel(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=128)
    displacement_type = ArrayField(base_field=enum.EnumField(Crisis.CRISIS_TYPE, null=False),
                                   blank=True, null=True)
    event_regions = models.ManyToManyField('country.CountryRegion', verbose_name=_('Regions'),
                                           blank=True, related_name='+')
    event_countries = models.ManyToManyField('country.Country', verbose_name=_('Countries'),
                                             blank=True, related_name='+')
    event_crises = models.ManyToManyField('crisis.Crisis', verbose_name=_('Crises'),
                                          blank=True, related_name='+')
    figure_categories = models.ManyToManyField('entry.FigureCategory',
                                               verbose_name=_('figure categories'),
                                               related_name='+', blank=True)
    figure_start_after = models.DateField(verbose_name=_('From Date'), blank=True, null=True)
    figure_end_before = models.DateField(verbose_name=_('To Date'), blank=True, null=True)
    figure_roles = ArrayField(base_field=enum.EnumField(enum=Figure.ROLE),
                              blank=True, null=True)
    entry_tags = models.ManyToManyField('entry.FigureTag', verbose_name=_('Figure Tags'),
                                        blank=True, related_name='+')
    entry_article_title = models.TextField(verbose_name=_('Article Title'),
                                           blank=True, null=True)
    event_crisis_types = ArrayField(enum.EnumField(enum=Crisis.CRISIS_TYPE),
                                    blank=True, null=True)

    class Meta:
        abstract = True


class ExtractionQuery(MetaInformationAbstractModel, QueryAbstractModel):
    @classmethod
    def get_entries(cls, data=None) -> ['Entry']:  # noqa
        return EntryExtractionFilterSet(data=data).qs

    @property
    def entries(self) -> ['Entry']:  # noqa
        return self.get_entries(data=dict(
            displacement_type=self.displacement_type,
            event_countries=self.event_countries.all(),
            event_regions=self.event_regions.all(),
            event_crises=self.event_crises.all(),
            figure_categories=self.figure_categories.all(),
            entry_tags=self.entry_tags.all(),
            figure_roles=self.figure_roles,
            figure_start_after=self.figure_start_after,
            figure_end_before=self.figure_end_before,
            entry_article_title=self.entry_article_title,
            event_crisis_types=self.event_crisis_types,
        ))
