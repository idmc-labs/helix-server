from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.contrib.models import MetaInformationAbstractModel
from apps.entry.models import Entry


class CountryRegion(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=256)

    def __str__(self):
        return self.name


class Country(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=256)
    region = models.ForeignKey('CountryRegion', verbose_name=_('Region'),
                               related_name='countries', on_delete=models.PROTECT)

    @property
    def entries(self):
        return Entry.objects.filter(event__countries=self.id)

    @property
    def last_contextual_update(self):
        return self.contextual_updates.last()

    @property
    def last_summary(self):
        return self.summaries.last()

    def __str__(self):
        return self.name


class ContextualUpdate(MetaInformationAbstractModel, models.Model):
    country = models.ForeignKey('Country', verbose_name=_('Country'),
                                on_delete=models.CASCADE, related_name='contextual_updates')
    update = models.TextField(verbose_name=_('Update'), blank=False)


class Summary(MetaInformationAbstractModel, models.Model):
    country = models.ForeignKey('Country', verbose_name=_('Country'),
                                on_delete=models.CASCADE, related_name='summaries')
    summary = models.TextField(verbose_name=_('Summary'), blank=False)
