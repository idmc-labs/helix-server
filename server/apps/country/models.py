from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils.translation import gettext_lazy as _

from apps.contrib.models import MetaInformationAbstractModel
from apps.entry.models import Entry


class GeographicalGroup(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=256)

    def __str__(self):
        return self.name


class CountryRegion(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=256)

    def __str__(self):
        return self.name


class Country(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=256)
    geographical_group = models.ForeignKey('GeographicalGroup', verbose_name=_('Geographical Group'), null=True,
                                           on_delete=models.SET_NULL)
    region = models.ForeignKey('CountryRegion', verbose_name=_('Region'),
                               related_name='countries', on_delete=models.PROTECT)
    sub_region = models.CharField(verbose_name=_('Sub Region'), max_length=256, null=True)

    iso3 = models.CharField(verbose_name=_('ISO3'), max_length=5,
                            null=True, blank=True)
    country_code = models.PositiveSmallIntegerField(verbose_name=_('Country Code'), null=True, blank=False)
    idmc_short_name = models.CharField(verbose_name=_('IDMC Short Name'), max_length=256, null=True, blank=False)
    idmc_full_name = models.CharField(verbose_name=_('IDMC Full Name'), max_length=256, null=True, blank=False)
    centroid = ArrayField(verbose_name=_('Centroid'), base_field=models.FloatField(blank=False), null=True)
    boundingbox = ArrayField(verbose_name=_('Bounding Box'), base_field=models.FloatField(blank=False), null=True)
    idmc_short_name_es = models.CharField(verbose_name=_('IDMC Short Name Es'), max_length=256, null=True)
    idmc_short_name_fr = models.CharField(verbose_name=_('IDMC Short Name Fr'), max_length=256, null=True)
    idmc_short_name_ar = models.CharField(verbose_name=_('IDMC Short Name Ar'), max_length=256, null=True)

    @property
    def entries(self):
        return Entry.objects.filter(event__countries=self.id).distinct()

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
