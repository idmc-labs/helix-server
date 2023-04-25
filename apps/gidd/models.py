from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum


class Conflict(models.Model):
    country = models.ForeignKey(
        'country.Country', related_name='country_conflict', on_delete=models.PROTECT,
        verbose_name=_('Country')
    )
    total_displacement = models.BigIntegerField(blank=True, null=True)
    new_displacement = models.BigIntegerField(blank=True, null=True)
    year = models.BigIntegerField()
    country_name = models.CharField(verbose_name=_('Name'), max_length=256)
    iso3 = models.CharField(verbose_name=_('ISO3'), max_length=5)

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
        related_name='gidd_events', on_delete=models.CASCADE, null=True, blank=True
    )
    event_name = models.CharField(verbose_name=_('Event name'), max_length=256)
    year = models.BigIntegerField()
    country = models.ForeignKey(
        'country.Country', related_name='country_disaster', on_delete=models.PROTECT,
        verbose_name=_('Country')
    )
    country_name = models.CharField(verbose_name=_('Name'), max_length=256)
    iso3 = models.CharField(verbose_name=_('ISO3'), max_length=5)

    # Dates
    start_date = models.DateField(blank=True, null=True)
    start_date_accuracy = models.TextField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    end_date_accuracy = models.TextField(blank=True, null=True)

    hazard_category_name = models.CharField(max_length=256, blank=True)
    hazard_sub_category_name = models.CharField(max_length=256, blank=True)
    hazard_sub_type_name = models.CharField(max_length=256, blank=True)
    hazard_type_name = models.CharField(max_length=256, blank=True)

    hazard_category = models.ForeignKey(
        'event.DisasterCategory', verbose_name=_('Hazard Category'),
        related_name='disasters', null=True, on_delete=models.SET_NULL
    )
    hazard_sub_category = models.ForeignKey(
        'event.DisasterSubCategory', verbose_name=_('Hazard Sub Category'),
        related_name='disasters', null=True, on_delete=models.SET_NULL
    )
    hazard_type = models.ForeignKey(
        'event.DisasterType', verbose_name=_('Hazard Type'),
        related_name='disasters', null=True, on_delete=models.SET_NULL
    )
    hazard_sub_type = models.ForeignKey(
        'event.DisasterSubType', verbose_name=_('Hazard Sub Type'),
        related_name='disasters', null=True, on_delete=models.SET_NULL
    )

    new_displacement = models.BigIntegerField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Disaster')
        verbose_name_plural = _('Disasters')

    def __str__(self):
        return str(self.id)


class StatusLog(models.Model):

    class Status(enum.Enum):
        PENDING = 0
        SUCCESS = 1
        FAILED = 2

        __labels__ = {
            PENDING: _("Pending"),
            SUCCESS: _("Success"),
            FAILED: _("Failed"),
        }
    triggered_by = models.ForeignKey(
        'users.User', verbose_name=_('Triggered by'), null=True, blank=True,
        related_name='gidd_data_triggered_by', on_delete=models.SET_NULL
    )
    triggered_at = models.DateTimeField(verbose_name='Triggered at', auto_now_add=True)
    completed_at = models.DateTimeField(verbose_name='Completed at', null=True, blank=True)
    status = enum.EnumField(
        verbose_name=_('Status'), enum=Status, default=Status.PENDING
    )

    class Meta:
        permissions = (
            ('update_gidd_data', 'Can update gidd data'),
        )

    def __str__(self):
        return str(self.triggered_at)


class ConflictLegacy(models.Model):
    total_displacement = models.BigIntegerField(blank=True, null=True)
    new_displacement = models.BigIntegerField(blank=True, null=True)
    year = models.BigIntegerField()
    country_name = models.CharField(verbose_name=_('Name'), max_length=256)
    iso3 = models.CharField(verbose_name=_('ISO3'), max_length=5)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Legacy conflict')
        verbose_name_plural = _('Legacy conflicts')

    def __str__(self):
        return str(self.id)


class DisasterLegacy(models.Model):
    year = models.BigIntegerField()
    country_name = models.CharField(verbose_name=_('Name'), max_length=256)
    iso3 = models.CharField(verbose_name=_('ISO3'), max_length=5)
    event_name = models.CharField(verbose_name=_('Event name'), max_length=256)

    # Dates
    start_date = models.DateField(blank=True, null=True)
    start_date_accuracy = models.TextField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    end_date_accuracy = models.TextField(blank=True, null=True)

    hazard_category_name = models.CharField(max_length=256, blank=True)
    hazard_sub_category_name = models.CharField(max_length=256, blank=True)
    hazard_sub_type_name = models.CharField(max_length=256, blank=True)
    hazard_type_name = models.CharField(max_length=256, blank=True)

    hazard_category = models.ForeignKey(
        'event.DisasterCategory', verbose_name=_('Hazard Category'),
        null=True,
        related_name='legacy_disasters', on_delete=models.SET_NULL
    )
    hazard_sub_category = models.ForeignKey(
        'event.DisasterSubCategory', verbose_name=_('Hazard Sub Category'),
        null=True,
        related_name='legacy_disasters', on_delete=models.SET_NULL
    )
    hazard_type = models.ForeignKey(
        'event.DisasterType', verbose_name=_('Hazard Type'),
        null=True,
        related_name='legacy_disasters', on_delete=models.SET_NULL
    )
    hazard_sub_type = models.ForeignKey(
        'event.DisasterSubType', verbose_name=_('Hazard Sub Type'),
        null=True,
        related_name='legacy_disasters', on_delete=models.SET_NULL
    )

    new_displacement = models.BigIntegerField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Legacy disaster')
        verbose_name_plural = _('Legacy disasters')

    def __str__(self):
        return str(self.id)


class ReleaseMetadata(models.Model):
    production_year = models.IntegerField(verbose_name=_('Production year'))
    staging_year = models.IntegerField(verbose_name=_('Staging year'))
    modified_by = models.ForeignKey(
        'users.User', verbose_name=_('Modified by'), null=True, blank=True,
        related_name='+', on_delete=models.SET_NULL
    )
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.production_year)
