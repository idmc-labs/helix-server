from django.db import models
from django.utils.translation import gettext_lazy as _


class CountryRegion(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=256)


class Country(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=256)
    region = models.ForeignKey('CountryRegion', verbose_name=_('Region'),
                               related_name='countries', on_delete=models.PROTECT)

    def __str__(self):
        return self.name
