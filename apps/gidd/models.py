from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField


class Conflict(models.Model):
    country = models.ForeignKey(
        'country.Country', related_name='country_conflict', on_delete=models.PROTECT,
        verbose_name=_('Country'), null=True, blank=True
    )
    total_displacement = models.BigIntegerField(blank=True, null=True)
    new_displacement = models.BigIntegerField(blank=True, null=True)
    year = models.BigIntegerField()
    country_name = models.CharField(verbose_name=_('Name'), max_length=256, null=True, blank=True)
    iso3 = models.CharField(verbose_name=_('ISO3'), max_length=5, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Conflict')
        verbose_name_plural = _('Conflicts')

    def __str__(self):
        return str(self.id)


class Disaster(models.Model):
    event = models.ForeignKey(
        'event.Event', verbose_name=_('Event'),
        related_name='gidd_figures', on_delete=models.CASCADE,
        null=True, blank=True
    )
    year = models.BigIntegerField()
    iso3 = ArrayField(verbose_name=_(
        "Iso3's"), base_field=models.CharField(max_length=5), blank=True, null=True
    )
    country_names = ArrayField(verbose_name=_(
        'Country names'), base_field=models.CharField(max_length=256), blank=True, null=True
    )

    # Dates
    start_date = models.DateField(blank=True, null=True)
    start_date_accuracy = models.TextField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    end_date_accuracy = models.TextField(blank=True, null=True)

    hazard_category = models.TextField(blank=True, null=True)
    hazard_sub_category = models.TextField(blank=True, null=True)
    hazard_sub_type = models.TextField(blank=True, null=True)
    hazard_type = models.TextField(blank=True, null=True)
    new_displacement = models.BigIntegerField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Disaster')
        verbose_name_plural = _('Disasters')

    def __str__(self):
        return str(self.id)
