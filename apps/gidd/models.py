from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum
from django.contrib.postgres.fields import ArrayField
from apps.crisis.models import Crisis
from apps.entry.models import Figure


class Conflict(models.Model):
    country = models.ForeignKey(
        'country.Country', related_name='country_conflict', on_delete=models.PROTECT,
        verbose_name=_('Country')
    )
    total_displacement = models.BigIntegerField(blank=True, null=True)
    new_displacement = models.BigIntegerField(blank=True, null=True)

    # Don't use these rounded fields to aggregate, just used to display and sort
    total_displacement_rounded = models.BigIntegerField(blank=True, null=True)
    new_displacement_rounded = models.BigIntegerField(blank=True, null=True)

    year = models.IntegerField()

    # Cached/Snapshot values
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
        related_name='gidd_events', on_delete=models.SET_NULL, null=True, blank=True
    )
    year = models.IntegerField()
    country = models.ForeignKey(
        'country.Country', related_name='country_disaster', on_delete=models.PROTECT,
        verbose_name=_('Country')
    )

    # Dates
    start_date = models.DateField(blank=True, null=True)
    start_date_accuracy = models.TextField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    end_date_accuracy = models.TextField(blank=True, null=True)

    hazard_category = models.ForeignKey(
        'event.DisasterCategory', verbose_name=_('Hazard Category'),
        related_name='disasters', on_delete=models.PROTECT
    )
    hazard_sub_category = models.ForeignKey(
        'event.DisasterSubCategory', verbose_name=_('Hazard Sub Category'),
        related_name='disasters', on_delete=models.PROTECT
    )
    hazard_type = models.ForeignKey(
        'event.DisasterType', verbose_name=_('Hazard Type'),
        related_name='disasters', on_delete=models.PROTECT
    )
    hazard_sub_type = models.ForeignKey(
        'event.DisasterSubType', verbose_name=_('Hazard Sub Type'),
        related_name='disasters', on_delete=models.PROTECT
    )

    new_displacement = models.BigIntegerField(blank=True, null=True)
    total_displacement = models.BigIntegerField(blank=True, null=True)

    # Don't use these rounded fields to aggregate, just used to display and sort
    total_displacement_rounded = models.BigIntegerField(blank=True, null=True)
    new_displacement_rounded = models.BigIntegerField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Cached/Snapshot values
    event_name = models.CharField(verbose_name=_('Event name'), max_length=256)
    iso3 = models.CharField(verbose_name=_('ISO3'), max_length=5)
    country_name = models.CharField(verbose_name=_('Name'), max_length=256)
    hazard_category_name = models.CharField(max_length=256, blank=True)
    hazard_sub_category_name = models.CharField(max_length=256, blank=True)
    hazard_sub_type_name = models.CharField(max_length=256, blank=True)
    hazard_type_name = models.CharField(max_length=256, blank=True)
    glide_numbers = ArrayField(
        models.CharField(
            verbose_name=_('Event Codes'), max_length=256
        ),
        default=list,
    )

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
        'users.User', verbose_name=_('Triggered by'),
        related_name='gidd_data_triggered_by', on_delete=models.PROTECT
    )
    triggered_at = models.DateTimeField(verbose_name='Triggered at', auto_now_add=True)
    completed_at = models.DateTimeField(verbose_name='Completed at', null=True, blank=True)
    status = enum.EnumField(
        verbose_name=_('Status'), enum=Status, default=Status.PENDING
    )

    class Meta:
        permissions = (
            ('update_gidd_data_gidd', 'Can update GIDD data'),
        )

    def __str__(self):
        return str(self.triggered_at)

    @classmethod
    def last_release_date(cls):
        return StatusLog.objects.last().completed_at.strftime("%d/%m/%Y")


class ConflictLegacy(models.Model):
    total_displacement = models.BigIntegerField(blank=True, null=True)
    new_displacement = models.BigIntegerField(blank=True, null=True)
    year = models.IntegerField()
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
    year = models.IntegerField()
    iso3 = models.CharField(verbose_name=_('ISO3'), max_length=5)
    event_name = models.CharField(verbose_name=_('Event name'), max_length=256)

    # Dates
    start_date = models.DateField(blank=True, null=True)
    start_date_accuracy = models.TextField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    end_date_accuracy = models.TextField(blank=True, null=True)

    hazard_category = models.ForeignKey(
        'event.DisasterCategory', verbose_name=_('Hazard Category'),
        related_name='legacy_disasters', on_delete=models.PROTECT
    )
    hazard_sub_category = models.ForeignKey(
        'event.DisasterSubCategory', verbose_name=_('Hazard Sub Category'),
        related_name='legacy_disasters', on_delete=models.PROTECT
    )
    hazard_type = models.ForeignKey(
        'event.DisasterType', verbose_name=_('Hazard Type'),
        related_name='legacy_disasters', on_delete=models.PROTECT
    )
    hazard_sub_type = models.ForeignKey(
        'event.DisasterSubType', verbose_name=_('Hazard Sub Type'),
        related_name='legacy_disasters', on_delete=models.PROTECT
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

    class ReleaseEnvironment(enum.Enum):
        PRE_RELEASE = 0
        RELEASE = 1

        __labels__ = {
            RELEASE: _("Release"),
            PRE_RELEASE: _("Pre Release"),
        }

    release_year = models.IntegerField(verbose_name=_('Release year'))
    pre_release_year = models.IntegerField(verbose_name=_('Pre-Release year'))
    modified_by = models.ForeignKey(
        'users.User', verbose_name=_('Modified by'),
        related_name='+', on_delete=models.PROTECT
    )
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.release_year)

    class Meta:
        permissions = (
            ('update_release_meta_data_gidd', 'Can update release meta data'),
        )


class PublicFigureAnalysis(models.Model):
    iso3 = models.CharField(verbose_name=_('ISO3'), max_length=5)
    figure_cause = enum.EnumField(Crisis.CRISIS_TYPE, verbose_name=_('Figure Cause'))
    figure_category = enum.EnumField(
        enum=Figure.FIGURE_CATEGORY_TYPES,
        verbose_name=_('Figure Category'),
    )
    year = models.IntegerField(verbose_name=_('Year'))
    figures = models.IntegerField(verbose_name=_('Figures'), null=True)
    description = models.TextField(verbose_name=_('Description'), null=True)
    report = models.ForeignKey(
        'report.Report', verbose_name=_('Report'), null=True,
        related_name='+', on_delete=models.SET_NULL
    )


class DisplacementData(models.Model):
    iso3 = models.CharField(verbose_name=_('ISO3'), max_length=5)
    country_name = models.CharField(verbose_name=_('Country name'), max_length=256)
    country = models.ForeignKey(
        'country.Country', related_name='displacements', on_delete=models.PROTECT,
        verbose_name=_('Country')
    )

    conflict_total_displacement = models.BigIntegerField(null=True, verbose_name=_('Conflict total idps'))
    conflict_new_displacement = models.BigIntegerField(null=True, verbose_name=_('Conflict total nd'))

    disaster_total_displacement = models.BigIntegerField(null=True, verbose_name=_('Disaster total nds'))
    disaster_new_displacement = models.BigIntegerField(null=True, verbose_name=_('Disaster total nd'))

    total_internal_displacement = models.BigIntegerField(null=True, verbose_name=_('Total internal displacement'))
    total_new_displacement = models.BigIntegerField(null=True, verbose_name=_('Total new displacement'))

    year = models.IntegerField(verbose_name=_('Year'))

    # Don't use these rounded fields to aggregate, just used to display and sort
    conflict_total_displacement_rounded = models.BigIntegerField(null=True, verbose_name=_('Conflict total idps'))
    conflict_new_displacement_rounded = models.BigIntegerField(null=True, verbose_name=_('Conflict total nd'))

    disaster_total_displacement_rounded = models.BigIntegerField(null=True, verbose_name=_('Disaster total nds'))
    disaster_new_displacement_rounded = models.BigIntegerField(null=True, verbose_name=_('Disaster total nd'))

    def __str__(self):
        return self.iso3


class IdpsSaddEstimate(models.Model):
    iso3 = models.CharField(verbose_name=_('ISO3'), max_length=5)
    country_name = models.CharField(verbose_name=_('Country name'), max_length=256)
    country = models.ForeignKey(
        'country.Country', related_name='ipds_sadd_estimates', on_delete=models.PROTECT,
        verbose_name=_('Country')
    )
    year = models.IntegerField()
    sex = models.CharField(verbose_name=_('Country name'), max_length=256)
    cause = enum.EnumField(Crisis.CRISIS_TYPE, verbose_name=_('Cause'))

    # This can be null
    zero_to_one = models.IntegerField(verbose_name=_('0-1'), null=True)
    zero_to_four = models.IntegerField(verbose_name=_('0-4'), null=True)
    zero_to_forteen = models.IntegerField(verbose_name=_('0-14'), null=True)
    zero_to_sventeen = models.IntegerField(verbose_name=_('0-17'), null=True)
    zero_to_twenty_four = models.IntegerField(verbose_name=_('0-24'), null=True)
    five_to_elaven = models.IntegerField(verbose_name=_('5-11'), null=True)
    five_to_fourteen = models.IntegerField(verbose_name=_('5-14'), null=True)
    twelve_to_fourteen = models.IntegerField(verbose_name=_('12-14'), null=True)
    twelve_to_sixteen = models.IntegerField(verbose_name=_('12-16'), null=True)
    fifteen_to_seventeen = models.IntegerField(verbose_name=_('15-17'), null=True)
    fifteen_to_twentyfour = models.IntegerField(verbose_name=_('15-24'), null=True)
    twenty_five_to_sixty_four = models.IntegerField(verbose_name=_('25-64'), null=True)
    sixty_five_plus = models.IntegerField(verbose_name=_('65+'), null=True)

    def __str__(self):
        return self.iso3
