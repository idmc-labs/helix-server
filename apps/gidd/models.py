from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum
from apps.crisis.models import Crisis
from apps.entry.models import Figure


class Conflict(models.Model):
    country = models.ForeignKey(
        'country.Country', related_name='country_conflict', on_delete=models.PROTECT,
        verbose_name=_('Country')
    )
    total_displacement = models.BigIntegerField(blank=True, null=True)
    new_displacement = models.BigIntegerField(blank=True, null=True)
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
        STAGING = 0
        PRODUCTION = 1

        __labels__ = {
            STAGING: _("Staging"),
            PRODUCTION: _("Production"),
        }

    production_year = models.IntegerField(verbose_name=_('Production year'))
    staging_year = models.IntegerField(verbose_name=_('Staging year'))
    modified_by = models.ForeignKey(
        'users.User', verbose_name=_('Modified by'),
        related_name='+', on_delete=models.PROTECT
    )
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.production_year)

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


class DisasterByHazardSubType(models.Model):
    disaster_total_idps = models.BigIntegerField(null=True, verbose_name=_('Disaster total nds'))
    disaster_total_nd = models.BigIntegerField(null=True, verbose_name=_('Disaster total nd'))
    hazard_sub_type = models.ForeignKey(
        'event.DisasterSubType', verbose_name=_('Hazard Sub Type'),
        related_name='displacements', on_delete=models.PROTECT
    )
    displacement = models.ForeignKey(
        'gidd.DisplacementData', verbose_name=_('Displacements'),
        related_name='disasters', on_delete=models.CASCADE,
    )


class DisplacementData(models.Model):
    iso3 = models.CharField(verbose_name=_('ISO3'), max_length=5)
    country_name = models.CharField(verbose_name=_('Country name'), max_length=256)
    country = models.ForeignKey(
        'country.Country', related_name='displacements', on_delete=models.PROTECT,
        verbose_name=_('Country')
    )
    conflict_total_idps = models.BigIntegerField(null=True, verbose_name=_('Conflict total idps'))
    conflict_total_nd = models.BigIntegerField(null=True, verbose_name=_('Conflict total nd'))
    cause = enum.EnumField(Crisis.CRISIS_TYPE, verbose_name=_('Cause'))
    year = models.IntegerField(verbose_name=_('Year'))

    def __str__(self):
        return self.iso3

    @classmethod
    def annotate_disaster_nd(cls, hazard_filter=None):
        if hazard_filter and hazard_filter['hazard_sub_type__in']:
            return {
                'disaster_total_nd': models.Subquery(
                    DisasterByHazardSubType.objects.filter(
                        displacement_id=models.OuterRef('pk'),
                        **hazard_filter,
                    ).annotate(
                        total=models.Sum('disaster_total_nd'),
                    ).order_by().values('total')[:1]
                )
            }
        else:
            return {'disaster_total_nd': models.Sum('disasters__disaster_total_nd')}

    @classmethod
    def annotate_disaster_idps(cls, hazard_filter=None):
        if hazard_filter and hazard_filter['hazard_sub_type__in']:
            return {
                'disaster_total_idps': models.Subquery(
                    DisasterByHazardSubType.objects.filter(
                        displacement_id=models.OuterRef('pk'),
                        **hazard_filter,
                    ).annotate(
                        total=models.Sum('disaster_total_idps'),
                    ).order_by().values('total')[:1]
                )
            }
        else:
            return {'disaster_total_idps': models.Sum('disasters__disaster_total_idps')}
