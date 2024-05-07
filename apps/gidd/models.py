from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum
from django.contrib.postgres.fields import ArrayField
from apps.contrib.commons import DATE_ACCURACY
from apps.contrib.models import MetaInformationAbstractModel
from apps.crisis.models import Crisis
from apps.entry.models import Figure, Entry


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

    displacement_occurred = ArrayField(
        base_field=enum.EnumField(
            Figure.DISPLACEMENT_OCCURRED,
            verbose_name=_('Displacement occurred'),
        ),
        default=list,
    )

    event_codes = ArrayField(
        models.CharField(
            verbose_name=_('Event Codes'), max_length=256
        ),
        default=list,
    )
    event_codes_type = ArrayField(
        models.CharField(
            verbose_name=_('Event Code Types'), max_length=256
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
        last_log = StatusLog.objects.last()
        return last_log.completed_at.strftime("%B %d, %Y") if last_log else None


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
        # XXX: Changing the attribute name will break external systems
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
    figures_rounded = models.IntegerField(verbose_name=_('Figures rounded'), null=True)
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
    sex = models.CharField(verbose_name=_('Sex'), max_length=256)
    cause = enum.EnumField(Crisis.CRISIS_TYPE, verbose_name=_('Cause'))

    # This can be null
    zero_to_four = models.IntegerField(verbose_name=_('0-4'), null=True)
    five_to_eleven = models.IntegerField(verbose_name=_('5-11'), null=True)
    twelve_to_seventeen = models.IntegerField(verbose_name=_('12-17'), null=True)
    eighteen_to_fiftynine = models.IntegerField(verbose_name=_('18-59'), null=True)
    sixty_plus = models.IntegerField(verbose_name=_('60+'), null=True)

    def __str__(self):
        return self.iso3


class GiddEvent(MetaInformationAbstractModel):
    name = models.CharField(verbose_name=_('Event Name'), max_length=256)
    event = models.ForeignKey(
        'event.Event', verbose_name=_('Event'),
        related_name='+', on_delete=models.SET_NULL, null=True, blank=True
    )
    cause = enum.EnumField(Crisis.CRISIS_TYPE, verbose_name=_('Cause'))
    # Dates
    start_date = models.DateField(blank=True, null=True)
    start_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_('Start Date Accuracy'),
        default=DATE_ACCURACY.DAY,
        blank=True,
        null=True,
    )
    end_date = models.DateField(blank=True, null=True)
    end_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_('End date accuracy'),
        blank=True,
        null=True,
    )

    event_codes = ArrayField(
        models.CharField(
            verbose_name=_('Event Codes'), max_length=256
        ),
        default=list,
    )
    event_codes_type = ArrayField(
        models.IntegerField(
            verbose_name=_('Event Code Types'),
        ),
        default=list,
    )
    event_codes_iso3 = ArrayField(
        models.CharField(
            verbose_name=_('Event Code ISO3'), max_length=256
        ),
        default=list,
    )
    event_codes_ids = ArrayField(
        models.IntegerField(
            verbose_name=_('Event Code IDs'),
        ),
        default=list,
    )
    violence = models.ForeignKey(
        'event.Violence', verbose_name=_('Violence'),
        blank=False, null=True,
        related_name='+', on_delete=models.SET_NULL
    )
    violence_sub_type = models.ForeignKey(
        'event.ViolenceSubType', verbose_name=_('Violence Sub Type'),
        blank=True, null=True,
        related_name='+', on_delete=models.SET_NULL
    )
    disaster_category = models.ForeignKey(
        'event.DisasterCategory', verbose_name=_('Hazard Category'),
        blank=True, null=True,
        related_name='+', on_delete=models.SET_NULL
    )
    disaster_sub_category = models.ForeignKey(
        'event.DisasterSubCategory', verbose_name=_('Hazard Sub Category'),
        blank=True, null=True,
        related_name='+', on_delete=models.SET_NULL
    )
    disaster_type = models.ForeignKey(
        'event.DisasterType', verbose_name=_('Hazard Type'),
        blank=True, null=True,
        related_name='+', on_delete=models.SET_NULL
    )
    disaster_sub_type = models.ForeignKey(
        'event.DisasterSubType', verbose_name=_('Hazard Sub Type'),
        blank=True, null=True,
        related_name='+', on_delete=models.SET_NULL
    )
    other_sub_type = models.ForeignKey(
        'event.OtherSubType', verbose_name=_('Other sub type'),
        blank=True, null=True,
        related_name='+', on_delete=models.SET_NULL)
    osv_sub_type = models.ForeignKey(
        'event.OsvSubType', verbose_name=_('OSV sub type'),
        blank=True, null=True, related_name='+',
        on_delete=models.SET_NULL
    )

    violence_name = models.CharField(max_length=256, blank=True, null=True)
    violence_sub_type_name = models.CharField(max_length=256, blank=True, null=True)
    disaster_category_name = models.CharField(max_length=256, blank=True, null=True)
    disaster_sub_category_name = models.CharField(max_length=256, blank=True, null=True)
    disaster_type_name = models.CharField(max_length=256, blank=True, null=True)
    disaster_sub_type_name = models.CharField(max_length=256, blank=True, null=True)
    other_sub_type_name = models.CharField(max_length=256, blank=True, null=True)
    osv_sub_type_name = models.CharField(max_length=256, blank=True, null=True)

    def __str__(self):
        return self.name


class GiddFigure(MetaInformationAbstractModel):
    iso3 = models.CharField(verbose_name=_('ISO3'), max_length=5)
    figure = models.ForeignKey(
        Figure,
        related_name='+', on_delete=models.SET_NULL, null=True, blank=True,
    )
    country_name = models.CharField(verbose_name=_('Country name'), max_length=256)
    country = models.ForeignKey(
        'country.Country', related_name='gidd_figures', on_delete=models.PROTECT,
        verbose_name=_('Country')
    )
    geographical_region_name = models.CharField(
        verbose_name=_('Geographical Region'), max_length=256, blank=True, null=True
    )
    term = enum.EnumField(
        enum=Figure.FIGURE_TERMS,
        verbose_name=_('Figure Term'),
        blank=True, null=True
    )
    year = models.IntegerField()
    unit = enum.EnumField(enum=Figure.UNIT, verbose_name=_('Unit of Figure'))
    category = enum.EnumField(
        enum=Figure.FIGURE_CATEGORY_TYPES,
        verbose_name=_('Figure Category'),
        blank=True, null=True
    )
    cause = enum.EnumField(
        enum=Crisis.CRISIS_TYPE,
        verbose_name=_('Figure Cause'),
        blank=True, null=True
    )
    total_figures = models.PositiveIntegerField(verbose_name=_('Total Figures'))
    household_size = models.FloatField(
        verbose_name=_('Household Size'),
        blank=True, null=True
    )
    quantifier = enum.EnumField(
        enum=Figure.QUANTIFIER,
        verbose_name=_('Quantifier'),
        null=True,
    )
    reported = models.PositiveIntegerField(verbose_name=_('Reported Figures'))
    role = enum.EnumField(enum=Figure.ROLE, verbose_name=_('Role'), default=Figure.ROLE.RECOMMENDED)
    # Dates
    start_date = models.DateField(blank=True, null=True)
    start_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_('Start Date Accuracy'),
        default=DATE_ACCURACY.DAY,
        blank=True,
        null=True,
    )
    end_date = models.DateField(blank=True, null=True)
    end_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_('End date accuracy'),
        blank=True,
        null=True,
    )
    stock_date = models.DateField(blank=True, null=True)
    stock_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_('Stock date accuracy'),
        blank=True,
        null=True,
    )
    stock_reporting_date = models.DateField(blank=True, null=True)
    include_idu = models.BooleanField(
        verbose_name=_('Include in IDU'),
        null=True,
    )
    excerpt_idu = models.TextField(
        verbose_name=_('Excerpt for IDU'),
        blank=True,
        null=True
    )
    is_confidential = models.BooleanField(
        verbose_name=_('Confidential Source'),
        default=False,
    )
    source_excerpt = models.TextField(
        verbose_name=_('Excerpt from Source'),
        blank=True,
        null=True
    )
    sources = ArrayField(
        models.CharField(
            verbose_name=_('Sources'), max_length=256
        ),
        default=list,
    )
    sources_ids = ArrayField(
        models.IntegerField(
            verbose_name=_('Sources IDs'),
        ),
        default=list,
    )
    sources_type = ArrayField(
        models.CharField(
            verbose_name=_('Sources Type'), max_length=256
        ),
        default=list,
    )
    publishers_ids = ArrayField(
        models.IntegerField(
            verbose_name=_('Publishers IDs'),
        ),
        default=list,
    )
    publishers = ArrayField(
        models.CharField(
            verbose_name=_('Publishers'), max_length=256
        ),
        default=list,
    )
    publishers_type = ArrayField(
        models.CharField(
            verbose_name=_('Publishers Type'), max_length=256
        ),
        default=list,
    )

    gidd_event = models.ForeignKey(
        'gidd.GiddEvent', verbose_name=_('GIDD Event'),
        related_name='gidd_figures', on_delete=models.PROTECT
    )
    entry = models.ForeignKey(
        Entry,
        verbose_name=_('Entry'),
        related_name='gidd_figures',
        on_delete=models.SET_NULL,
        null=True,
    )
    entry_name = models.CharField(
        max_length=512,
        verbose_name=_('Entry Title'),
        blank=True,
        null=True
    )
    context_of_violence = ArrayField(
        models.CharField(
            verbose_name=_('Context of Violences'), max_length=256
        ),
        default=list,
    )
    context_of_violence_ids = ArrayField(
        models.IntegerField(
            verbose_name=_('Context of Violence IDs'),
        ),
        default=list,
    )
    calculation_logic = models.TextField(
        verbose_name=_('Analysis and Calculation Logic'),
        blank=True,
        null=True
    )
    tags = ArrayField(
        models.CharField(
            verbose_name=_('Tags'), max_length=256
        ),
        default=list,
    )
    tags_ids = ArrayField(
        models.IntegerField(
            verbose_name=_('Tags IDs'),
        ),
        default=list,
    )
    is_housing_destruction = models.BooleanField(
        verbose_name=_('Is Housing Destruction'),
        default=False,
        null=True,
        blank=True,
    )
    is_disaggregated = models.BooleanField(
        verbose_name=_('Is disaggregated'),
        default=False
    )

    locations_ids = ArrayField(
        models.IntegerField(
            verbose_name=_('Location IDs'),
        ),
        default=list,
    )

    locations_coordinates = ArrayField(
        models.CharField(
            verbose_name=_('Location Coordinates'), max_length=256
        ),
        default=list,
    )
    locations_names = ArrayField(
        models.CharField(
            verbose_name=_('Location Names'), max_length=256
        ),
        default=list,
    )
    locations_accuracy = ArrayField(
        models.IntegerField(
            verbose_name=_('Location Accuracy'),
        ),
        default=list,
    )
    locations_type = ArrayField(
        models.IntegerField(
            verbose_name=_('Location Type'),
        ),
        default=list,
    )
    displacement_occurred = enum.EnumField(
        enum=Figure.DISPLACEMENT_OCCURRED,
        verbose_name=_('Displacement Occurred'),
        blank=True, null=True
    )
    violence = models.ForeignKey(
        'event.Violence', verbose_name=_('Figure Violence'),
        blank=False, null=True,
        related_name='+', on_delete=models.SET_NULL
    )
    violence_sub_type = models.ForeignKey(
        'event.ViolenceSubType', verbose_name=_('Figure Violence Sub Type'),
        blank=True, null=True,
        related_name='+', on_delete=models.SET_NULL
    )
    disaster_category = models.ForeignKey(
        'event.DisasterCategory', verbose_name=_('Figure Hazard Category'),
        blank=True, null=True,
        related_name='+', on_delete=models.SET_NULL
    )
    disaster_sub_category = models.ForeignKey(
        'event.DisasterSubCategory', verbose_name=_('Figure Hazard Sub Category'),
        blank=True, null=True,
        related_name='+', on_delete=models.SET_NULL
    )
    disaster_type = models.ForeignKey(
        'event.DisasterType', verbose_name=_('Figure Hazard Type'),
        blank=True, null=True,
        related_name='+', on_delete=models.SET_NULL
    )
    disaster_sub_type = models.ForeignKey(
        'event.DisasterSubType', verbose_name=_('Figure Hazard Sub Type'),
        blank=True, null=True,
        related_name='+', on_delete=models.SET_NULL
    )
    other_sub_type = models.ForeignKey(
        'event.OtherSubType', verbose_name=_('Other sub type'),
        blank=True, null=True,
        related_name='+', on_delete=models.SET_NULL)
    osv_sub_type = models.ForeignKey(
        'event.OsvSubType', verbose_name=_('Figure OSV sub type'),
        blank=True, null=True, related_name='+',
        on_delete=models.SET_NULL
    )

    violence_name = models.CharField(max_length=256, blank=True, null=True)
    violence_sub_type_name = models.CharField(max_length=256, blank=True, null=True)
    disaster_category_name = models.CharField(max_length=256, blank=True, null=True)
    disaster_sub_category_name = models.CharField(max_length=256, blank=True, null=True)
    disaster_type_name = models.CharField(max_length=256, blank=True, null=True)
    disaster_sub_type_name = models.CharField(max_length=256, blank=True, null=True)
    other_sub_type_name = models.CharField(max_length=256, blank=True, null=True)
    osv_sub_type_name = models.CharField(max_length=256, blank=True, null=True)

    def __str__(self):
        return self.iso3
