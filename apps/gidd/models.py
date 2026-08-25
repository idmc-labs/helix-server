import datetime
import typing

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.commons import DATE_ACCURACY
from apps.contrib.models import MetaInformationAbstractModel
from apps.crisis.models import Crisis
from apps.entry.models import Entry, Figure
from utils.fields import UnbleachedTextField


class Conflict(models.Model):
    # Bounded to what GiddConflictType exposes: these lists are unauthenticated, and a column a
    # caller cannot read back buys it nothing while widening what it can make the database do.
    # To-many paths stay out because they fan the parent list out
    # (apps/contrib/tests/test_to_many_ordering_fanout.py).
    ORDERING_ALLOWLIST = frozenset(
        {
            "country_name",
            "id",
            "iso3",
            "new_displacement",
            "new_displacement_rounded",
            "total_displacement",
            "total_displacement_rounded",
            "year",
        }
    )

    country = models.ForeignKey(
        "country.Country", related_name="country_conflict", on_delete=models.PROTECT, verbose_name=_("Country")
    )
    total_displacement = models.BigIntegerField(blank=True, null=True)
    new_displacement = models.BigIntegerField(blank=True, null=True)

    # Don't use these rounded fields to aggregate, just used to display and sort
    total_displacement_rounded = models.BigIntegerField(blank=True, null=True)
    new_displacement_rounded = models.BigIntegerField(blank=True, null=True)

    year = models.IntegerField()

    # Cached/Snapshot values
    country_name = models.CharField(verbose_name=_("Name"), max_length=256)
    iso3 = models.CharField(verbose_name=_("ISO3"), max_length=5)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Conflict")
        verbose_name_plural = _("Conflicts")

    def __str__(self):
        return str(self.id)


class Disaster(models.Model):
    # See Conflict. The type exposes the `*_name` denormalisations and not the hazard FKs, so the
    # REST serializer -- which exposes both -- ends up with a wider set than this.
    ORDERING_ALLOWLIST = frozenset(
        {
            "country_name",
            "end_date",
            "end_date_accuracy",
            "event_codes",
            "event_codes_type",
            "event_name",
            "hazard_category_name",
            "hazard_sub_category_name",
            "hazard_sub_type_name",
            "hazard_type_name",
            "id",
            "iso3",
            "new_displacement",
            "new_displacement_rounded",
            "start_date",
            "start_date_accuracy",
            "total_displacement",
            "total_displacement_rounded",
            "year",
        }
    )

    event = models.ForeignKey(
        "event.Event", verbose_name=_("Event"), related_name="gidd_events", on_delete=models.SET_NULL, null=True, blank=True
    )
    event_raw_id = models.IntegerField(null=True, blank=True)
    year = models.IntegerField()
    country = models.ForeignKey(
        "country.Country", related_name="country_disaster", on_delete=models.PROTECT, verbose_name=_("Country")
    )

    # Dates
    start_date = models.DateField(blank=True, null=True)
    start_date_accuracy = UnbleachedTextField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    end_date_accuracy = UnbleachedTextField(blank=True, null=True)

    hazard_category = models.ForeignKey(
        "event.DisasterCategory", verbose_name=_("Hazard Category"), related_name="disasters", on_delete=models.PROTECT
    )
    hazard_sub_category = models.ForeignKey(
        "event.DisasterSubCategory",
        verbose_name=_("Hazard Sub Category"),
        related_name="disasters",
        on_delete=models.PROTECT,
    )
    hazard_type = models.ForeignKey(
        "event.DisasterType", verbose_name=_("Hazard Type"), related_name="disasters", on_delete=models.PROTECT
    )
    hazard_sub_type = models.ForeignKey(
        "event.DisasterSubType", verbose_name=_("Hazard Sub Type"), related_name="disasters", on_delete=models.PROTECT
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
    event_name = models.CharField(verbose_name=_("Event name"), max_length=256)
    iso3 = models.CharField(verbose_name=_("ISO3"), max_length=5)
    country_name = models.CharField(verbose_name=_("Name"), max_length=256)
    hazard_category_name = models.CharField(max_length=256, blank=True)
    hazard_sub_category_name = models.CharField(max_length=256, blank=True)
    hazard_sub_type_name = models.CharField(max_length=256, blank=True)
    hazard_type_name = models.CharField(max_length=256, blank=True)

    displacement_occurred = ArrayField(
        base_field=enum.EnumField(
            Figure.DISPLACEMENT_OCCURRED,
            verbose_name=_("Displacement occurred"),
        ),
        default=list,
    )

    # Deprecated
    glide_numbers = ArrayField(
        models.CharField(verbose_name=_("Event Codes"), max_length=256),
        default=list,
    )
    event_codes = ArrayField(
        models.CharField(verbose_name=_("Event Codes"), max_length=256),
        default=list,
    )
    event_codes_type = ArrayField(
        models.CharField(verbose_name=_("Event Code Types"), max_length=256),
        default=list,
    )

    class Meta:
        verbose_name = _("Disaster")
        verbose_name_plural = _("Disasters")

    def __str__(self):
        return str(self.id)


class StatusLog(models.Model):
    # See Conflict, though this list is authenticated and small.
    ORDERING_ALLOWLIST = frozenset(
        {
            "completed_at",
            "id",
            "status",
            "triggered_at",
            "triggered_by",
        }
    )

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
        "users.User", verbose_name=_("Triggered by"), related_name="gidd_data_triggered_by", on_delete=models.PROTECT
    )
    triggered_at = models.DateTimeField(verbose_name="Triggered at", auto_now_add=True)
    completed_at = models.DateTimeField(verbose_name="Completed at", null=True, blank=True)
    status = enum.EnumField(verbose_name=_("Status"), enum=Status, default=Status.PENDING)

    # A run that died without flipping its status (killed worker: the transaction
    # rolls back but the PENDING log row survives) must not block triggers, and the
    # cleanup task marks it FAILED. Slightly above the task's 30-min hard ceiling
    # so a still-running generation is never flipped; the advisory lock in the task
    # is the real mutual exclusion.
    PENDING_STALE_AFTER = datetime.timedelta(minutes=35)

    class Meta:
        permissions = (("update_gidd_data_gidd", "Can update GIDD data"),)

    def __str__(self):
        return str(self.triggered_at)

    @classmethod
    def has_active_run(cls) -> bool:
        last_run = cls.objects.last()
        return bool(
            last_run
            and last_run.status == cls.Status.PENDING
            and last_run.triggered_at >= timezone.now() - cls.PENDING_STALE_AFTER
        )

    @classmethod
    def last_release_date(cls, format=None) -> typing.Optional[str]:
        # TODO: Do we need to handle for completed_at=null?
        last_log = StatusLog.objects.filter(status=cls.Status.SUCCESS).order_by("-completed_at").first()
        if last_log:
            _format = format or "%B %d, %Y"
            return last_log.completed_at.strftime(_format)


class ConflictLegacy(models.Model):
    """Pre-2016 conflict displacement, imported once from CSV.

    Nothing writes this table: the importer that populated it is gone and the generation derives
    every year it covers from `Figure`. It is retained because those rows are the only copy of the
    pre-2016 series in the system -- they are not derivable from Helix data.
    """

    total_displacement = models.BigIntegerField(blank=True, null=True)
    new_displacement = models.BigIntegerField(blank=True, null=True)
    year = models.IntegerField()
    iso3 = models.CharField(verbose_name=_("ISO3"), max_length=5)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Legacy conflict")
        verbose_name_plural = _("Legacy conflicts")

    def __str__(self):
        return str(self.id)


class DisasterLegacy(models.Model):
    """Pre-2016 disaster displacement, imported once from CSV. See ConflictLegacy."""

    year = models.IntegerField()
    iso3 = models.CharField(verbose_name=_("ISO3"), max_length=5)
    event_name = models.CharField(verbose_name=_("Event name"), max_length=256)

    # Dates
    start_date = models.DateField(blank=True, null=True)
    start_date_accuracy = UnbleachedTextField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    end_date_accuracy = UnbleachedTextField(blank=True, null=True)

    hazard_category = models.ForeignKey(
        "event.DisasterCategory",
        verbose_name=_("Hazard Category"),
        related_name="legacy_disasters",
        on_delete=models.PROTECT,
    )
    hazard_sub_category = models.ForeignKey(
        "event.DisasterSubCategory",
        verbose_name=_("Hazard Sub Category"),
        related_name="legacy_disasters",
        on_delete=models.PROTECT,
    )
    hazard_type = models.ForeignKey(
        "event.DisasterType", verbose_name=_("Hazard Type"), related_name="legacy_disasters", on_delete=models.PROTECT
    )
    hazard_sub_type = models.ForeignKey(
        "event.DisasterSubType", verbose_name=_("Hazard Sub Type"), related_name="legacy_disasters", on_delete=models.PROTECT
    )

    new_displacement = models.BigIntegerField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Legacy disaster")
        verbose_name_plural = _("Legacy disasters")

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

    release_year = models.IntegerField(verbose_name=_("Release year"))
    pre_release_year = models.IntegerField(verbose_name=_("Pre-Release year"))
    modified_by = models.ForeignKey("users.User", verbose_name=_("Modified by"), related_name="+", on_delete=models.PROTECT)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.release_year)

    class Meta:
        permissions = (("update_release_meta_data_gidd", "Can update release meta data"),)


class PublicFigureAnalysis(models.Model):
    # See Conflict. `description` is a TextField, so it is the most expensive key here.
    ORDERING_ALLOWLIST = frozenset(
        {
            "description",
            "figure_category",
            "figure_cause",
            "figures",
            "figures_rounded",
            "id",
            "iso3",
            "year",
        }
    )

    iso3 = models.CharField(verbose_name=_("ISO3"), max_length=5)
    figure_cause = enum.EnumField(Crisis.CRISIS_TYPE, verbose_name=_("Figure Cause"))
    figure_category = enum.EnumField(
        enum=Figure.FIGURE_CATEGORY_TYPES,
        verbose_name=_("Figure Category"),
    )
    year = models.IntegerField(verbose_name=_("Year"))
    figures = models.IntegerField(verbose_name=_("Figures"), null=True)
    figures_rounded = models.IntegerField(verbose_name=_("Figures rounded"), null=True)
    description = UnbleachedTextField(verbose_name=_("Description"), null=True)
    report = models.ForeignKey(
        "report.Report", verbose_name=_("Report"), null=True, related_name="+", on_delete=models.SET_NULL
    )
    report_raw_id = models.IntegerField()


class IdpsSaddEstimate(models.Model):
    iso3 = models.CharField(verbose_name=_("ISO3"), max_length=5)
    country_name = models.CharField(verbose_name=_("Country name"), max_length=256)
    country = models.ForeignKey(
        "country.Country", related_name="ipds_sadd_estimates", on_delete=models.PROTECT, verbose_name=_("Country")
    )
    year = models.IntegerField()
    sex = models.CharField(verbose_name=_("Sex"), max_length=256)
    cause = enum.EnumField(Crisis.CRISIS_TYPE, verbose_name=_("Cause"))

    # This can be null
    zero_to_four = models.IntegerField(verbose_name=_("0-4"), null=True)
    five_to_eleven = models.IntegerField(verbose_name=_("5-11"), null=True)
    twelve_to_seventeen = models.IntegerField(verbose_name=_("12-17"), null=True)
    eighteen_to_fiftynine = models.IntegerField(verbose_name=_("18-59"), null=True)
    sixty_plus = models.IntegerField(verbose_name=_("60+"), null=True)

    def __str__(self):
        return self.iso3


class GiddEvent(MetaInformationAbstractModel):
    name = models.CharField(verbose_name=_("Event Name"), max_length=256)
    event_raw_id = models.IntegerField(null=True, blank=True)
    event = models.ForeignKey(
        "event.Event", verbose_name=_("Event"), related_name="+", on_delete=models.SET_NULL, null=True, blank=True
    )
    cause = enum.EnumField(Crisis.CRISIS_TYPE, verbose_name=_("Cause"))
    # Dates
    start_date = models.DateField(blank=True, null=True)
    start_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_("Start Date Accuracy"),
        default=DATE_ACCURACY.DAY,
        blank=True,
        null=True,
    )
    end_date = models.DateField(blank=True, null=True)
    end_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_("End date accuracy"),
        blank=True,
        null=True,
    )

    # Deprecated
    glide_numbers = ArrayField(
        models.CharField(verbose_name=_("Event Codes"), max_length=256),
        default=list,
    )
    event_codes = ArrayField(
        models.CharField(verbose_name=_("Event Codes"), max_length=256),
        default=list,
    )
    event_codes_type = ArrayField(
        models.IntegerField(
            verbose_name=_("Event Code Types"),
        ),
        default=list,
    )
    event_codes_iso3 = ArrayField(
        models.CharField(verbose_name=_("Event Code ISO3"), max_length=256),
        default=list,
    )
    event_codes_ids = ArrayField(
        models.IntegerField(
            verbose_name=_("Event Code IDs"),
        ),
        default=list,
    )
    violence = models.ForeignKey(
        "event.Violence", verbose_name=_("Violence"), blank=False, null=True, related_name="+", on_delete=models.SET_NULL
    )
    violence_sub_type = models.ForeignKey(
        "event.ViolenceSubType",
        verbose_name=_("Violence Sub Type"),
        blank=True,
        null=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    disaster_category = models.ForeignKey(
        "event.DisasterCategory",
        verbose_name=_("Hazard Category"),
        blank=True,
        null=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    disaster_sub_category = models.ForeignKey(
        "event.DisasterSubCategory",
        verbose_name=_("Hazard Sub Category"),
        blank=True,
        null=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    disaster_type = models.ForeignKey(
        "event.DisasterType",
        verbose_name=_("Hazard Type"),
        blank=True,
        null=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    disaster_sub_type = models.ForeignKey(
        "event.DisasterSubType",
        verbose_name=_("Hazard Sub Type"),
        blank=True,
        null=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    other_sub_type = models.ForeignKey(
        "event.OtherSubType",
        verbose_name=_("Other sub type"),
        blank=True,
        null=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    osv_sub_type = models.ForeignKey(
        "event.OsvSubType",
        verbose_name=_("OSV sub type"),
        blank=True,
        null=True,
        related_name="+",
        on_delete=models.SET_NULL,
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
    iso3 = models.CharField(verbose_name=_("ISO3"), max_length=5)
    figure_raw_id = models.IntegerField(null=True, blank=True)
    figure = models.ForeignKey(
        Figure,
        related_name="+",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    country_name = models.CharField(verbose_name=_("Country name"), max_length=256)
    country = models.ForeignKey(
        "country.Country", related_name="gidd_figures", on_delete=models.PROTECT, verbose_name=_("Country")
    )
    geographical_region_name = models.CharField(verbose_name=_("Geographical Region"), max_length=256, blank=True, null=True)
    term = enum.EnumField(enum=Figure.FIGURE_TERMS, verbose_name=_("Figure Term"), blank=True, null=True)
    year = models.IntegerField()
    unit = enum.EnumField(enum=Figure.UNIT, verbose_name=_("Unit of Figure"))
    category = enum.EnumField(enum=Figure.FIGURE_CATEGORY_TYPES, verbose_name=_("Figure Category"), blank=True, null=True)
    cause = enum.EnumField(enum=Crisis.CRISIS_TYPE, verbose_name=_("Figure Cause"), blank=True, null=True)
    total_figures = models.PositiveIntegerField(verbose_name=_("Total Figures"))
    household_size = models.FloatField(verbose_name=_("Household Size"), blank=True, null=True)
    quantifier = enum.EnumField(
        enum=Figure.QUANTIFIER,
        verbose_name=_("Quantifier"),
        null=True,
    )
    reported = models.PositiveIntegerField(verbose_name=_("Reported Figures"))
    role = enum.EnumField(enum=Figure.ROLE, verbose_name=_("Role"), default=Figure.ROLE.RECOMMENDED)
    # Dates
    start_date = models.DateField(blank=True, null=True)
    start_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_("Start Date Accuracy"),
        default=DATE_ACCURACY.DAY,
        blank=True,
        null=True,
    )
    end_date = models.DateField(blank=True, null=True)
    end_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_("End date accuracy"),
        blank=True,
        null=True,
    )
    stock_date = models.DateField(blank=True, null=True)
    stock_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_("Stock date accuracy"),
        blank=True,
        null=True,
    )
    stock_reporting_date = models.DateField(blank=True, null=True)
    include_idu = models.BooleanField(
        verbose_name=_("Include in IDU"),
        null=True,
    )
    excerpt_idu = UnbleachedTextField(verbose_name=_("Excerpt for IDU"), blank=True, null=True)
    is_confidential = models.BooleanField(
        verbose_name=_("Confidential Source"),
        default=False,
    )
    source_excerpt = UnbleachedTextField(verbose_name=_("Excerpt from Source"), blank=True, null=True)
    sources = ArrayField(
        models.CharField(verbose_name=_("Sources"), max_length=256),
        default=list,
    )
    sources_ids = ArrayField(
        models.IntegerField(
            verbose_name=_("Sources IDs"),
        ),
        default=list,
    )
    sources_type = ArrayField(
        models.CharField(verbose_name=_("Sources Type"), max_length=256),
        default=list,
    )
    publishers_ids = ArrayField(
        models.IntegerField(
            verbose_name=_("Publishers IDs"),
        ),
        default=list,
    )
    publishers = ArrayField(
        models.CharField(verbose_name=_("Publishers"), max_length=256),
        default=list,
    )
    publishers_type = ArrayField(
        models.CharField(verbose_name=_("Publishers Type"), max_length=256),
        default=list,
    )

    # NOTE: Gidd event id and event id must be same
    gidd_event = models.ForeignKey(
        "gidd.GiddEvent", verbose_name=_("GIDD Event"), related_name="gidd_figures", on_delete=models.PROTECT
    )
    entry = models.ForeignKey(
        Entry,
        verbose_name=_("Entry"),
        related_name="gidd_figures",
        on_delete=models.SET_NULL,
        null=True,
    )
    entry_raw_id = models.IntegerField(null=True, blank=True)
    entry_name = models.CharField(max_length=512, verbose_name=_("Entry Title"), blank=True, null=True)
    context_of_violence = ArrayField(
        models.CharField(verbose_name=_("Context of Violences"), max_length=256),
        default=list,
    )
    context_of_violence_ids = ArrayField(
        models.IntegerField(
            verbose_name=_("Context of Violence IDs"),
        ),
        default=list,
    )
    calculation_logic = UnbleachedTextField(verbose_name=_("Analysis and Calculation Logic"), blank=True, null=True)
    tags = ArrayField(
        models.CharField(verbose_name=_("Tags"), max_length=256),
        default=list,
    )
    tags_ids = ArrayField(
        models.IntegerField(
            verbose_name=_("Tags IDs"),
        ),
        default=list,
    )
    is_housing_destruction = models.BooleanField(
        verbose_name=_("Is Housing Destruction"),
        default=False,
        null=True,
        blank=True,
    )
    is_disaggregated = models.BooleanField(verbose_name=_("Is disaggregated"), default=False)

    locations_ids = ArrayField(
        models.IntegerField(
            verbose_name=_("Location IDs"),
        ),
        default=list,
    )

    locations_coordinates = ArrayField(
        models.CharField(verbose_name=_("Location Coordinates"), max_length=256),
        default=list,
    )
    locations_names = ArrayField(
        models.CharField(verbose_name=_("Location Names"), max_length=256),
        default=list,
    )
    locations_accuracy = ArrayField(
        models.IntegerField(
            verbose_name=_("Location Accuracy"),
        ),
        default=list,
    )
    locations_type = ArrayField(
        models.IntegerField(
            verbose_name=_("Location Type"),
        ),
        default=list,
    )
    displacement_occurred = enum.EnumField(
        enum=Figure.DISPLACEMENT_OCCURRED, verbose_name=_("Displacement Occurred"), blank=True, null=True
    )
    violence = models.ForeignKey(
        "event.Violence",
        verbose_name=_("Figure Violence"),
        blank=False,
        null=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    violence_sub_type = models.ForeignKey(
        "event.ViolenceSubType",
        verbose_name=_("Figure Violence Sub Type"),
        blank=True,
        null=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    disaster_category = models.ForeignKey(
        "event.DisasterCategory",
        verbose_name=_("Figure Hazard Category"),
        blank=True,
        null=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    disaster_sub_category = models.ForeignKey(
        "event.DisasterSubCategory",
        verbose_name=_("Figure Hazard Sub Category"),
        blank=True,
        null=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    disaster_type = models.ForeignKey(
        "event.DisasterType",
        verbose_name=_("Figure Hazard Type"),
        blank=True,
        null=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    disaster_sub_type = models.ForeignKey(
        "event.DisasterSubType",
        verbose_name=_("Figure Hazard Sub Type"),
        blank=True,
        null=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    other_sub_type = models.ForeignKey(
        "event.OtherSubType",
        verbose_name=_("Other sub type"),
        blank=True,
        null=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    osv_sub_type = models.ForeignKey(
        "event.OsvSubType",
        verbose_name=_("Figure OSV sub type"),
        blank=True,
        null=True,
        related_name="+",
        on_delete=models.SET_NULL,
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


class GiddDisplacement(models.Model):
    """
    Displacement figures aggregated by country + year + cause + violence/hazard subtype.
    Conflict rows: violence + violence_sub_type set; hazard fields null.
    Disaster rows: hazard_type + hazard_sub_type set; violence fields null.
    """

    country = models.ForeignKey("country.Country", related_name="gidd_displacements", on_delete=models.PROTECT)
    iso3 = models.CharField(verbose_name=_("ISO3"), max_length=5)
    country_name = models.CharField(verbose_name=_("Country name"), max_length=256)
    year = models.IntegerField()
    cause = enum.EnumField(Crisis.CRISIS_TYPE, verbose_name=_("Cause"))

    # Conflict fields (null for disaster rows)
    violence = models.ForeignKey("event.Violence", null=True, blank=True, related_name="+", on_delete=models.SET_NULL)
    violence_name = models.CharField(max_length=256, blank=True, null=True)
    violence_sub_type = models.ForeignKey(
        "event.ViolenceSubType", null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )
    violence_sub_type_name = models.CharField(max_length=256, blank=True, null=True)

    # Disaster fields (null for conflict rows)
    hazard_category = models.ForeignKey(
        "event.DisasterCategory", null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )
    hazard_category_name = models.CharField(max_length=256, blank=True, null=True)
    hazard_sub_category = models.ForeignKey(
        "event.DisasterSubCategory", null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )
    hazard_sub_category_name = models.CharField(max_length=256, blank=True, null=True)
    hazard_type = models.ForeignKey("event.DisasterType", null=True, blank=True, related_name="+", on_delete=models.SET_NULL)
    hazard_type_name = models.CharField(max_length=256, blank=True, null=True)
    hazard_sub_type = models.ForeignKey(
        "event.DisasterSubType", null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )
    hazard_sub_type_name = models.CharField(max_length=256, blank=True, null=True)

    new_displacement = models.BigIntegerField(blank=True, null=True)
    new_displacement_rounded = models.BigIntegerField(blank=True, null=True)
    total_displacement = models.BigIntegerField(blank=True, null=True)
    total_displacement_rounded = models.BigIntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("GIDD Disaggregated Displacement")
        verbose_name_plural = _("GIDD Disaggregated Displacements")

    def __str__(self):
        return f"{self.iso3} - {self.year} - {self.cause}"


class GiddEventDisplacement(models.Model):
    """
    Displacement figures per event + country + year + cause + violence/hazard subtype.
    Unified event-level table for both conflict and disaster.
    Conflict rows: violence + violence_sub_type set; hazard fields null.
    Disaster rows: hazard_type + hazard_sub_type set; violence fields null.
    """

    # giddPublicEvents (replaces the old giddPublicDisasters). Unauthenticated; the frontend
    # Gidd/EventsTable sortable columns (mirrors the retired Disaster.ORDERING_ALLOWLIST).
    ORDERING_ALLOWLIST = frozenset(
        {
            "country_name",
            "created_at",
            "event_codes",
            "event_name",
            "hazard_category_name",
            "hazard_type_name",
            "id",
            "new_displacement_rounded",
            "start_date",
            "year",
        }
    )

    event = models.ForeignKey("event.Event", null=True, blank=True, related_name="+", on_delete=models.SET_NULL)
    event_raw_id = models.IntegerField(null=True, blank=True)
    event_name = models.CharField(verbose_name=_("Event name"), max_length=256)

    country = models.ForeignKey("country.Country", related_name="gidd_event_displacements", on_delete=models.PROTECT)
    iso3 = models.CharField(verbose_name=_("ISO3"), max_length=5)
    country_name = models.CharField(verbose_name=_("Country name"), max_length=256)
    year = models.IntegerField()
    cause = enum.EnumField(Crisis.CRISIS_TYPE, verbose_name=_("Cause"))

    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    event_codes = ArrayField(models.CharField(verbose_name=_("Event Codes"), max_length=256), default=list)
    # REST-only fields — mirror the old Disaster table so the /gidd/disasters/ dump stays identical.
    # Not exposed in GraphQL.
    start_date_accuracy = models.TextField(blank=True, null=True)
    end_date_accuracy = models.TextField(blank=True, null=True)
    event_codes_type = ArrayField(models.CharField(verbose_name=_("Event Code Types"), max_length=256), default=list)
    glide_numbers = ArrayField(models.CharField(verbose_name=_("Glide Numbers"), max_length=256), default=list)
    displacement_occurred = ArrayField(
        base_field=enum.EnumField(Figure.DISPLACEMENT_OCCURRED, verbose_name=_("Displacement occurred")),
        default=list,
    )

    # Conflict fields (null for disaster rows)
    violence = models.ForeignKey("event.Violence", null=True, blank=True, related_name="+", on_delete=models.SET_NULL)
    violence_name = models.CharField(max_length=256, blank=True, null=True)
    violence_sub_type = models.ForeignKey(
        "event.ViolenceSubType", null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )
    violence_sub_type_name = models.CharField(max_length=256, blank=True, null=True)

    # Disaster fields (null for conflict rows)
    hazard_category = models.ForeignKey(
        "event.DisasterCategory", null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )
    hazard_category_name = models.CharField(max_length=256, blank=True, null=True)
    hazard_sub_category = models.ForeignKey(
        "event.DisasterSubCategory", null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )
    hazard_sub_category_name = models.CharField(max_length=256, blank=True, null=True)
    hazard_type = models.ForeignKey("event.DisasterType", null=True, blank=True, related_name="+", on_delete=models.SET_NULL)
    hazard_type_name = models.CharField(max_length=256, blank=True, null=True)
    hazard_sub_type = models.ForeignKey(
        "event.DisasterSubType", null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )
    hazard_sub_type_name = models.CharField(max_length=256, blank=True, null=True)

    new_displacement = models.BigIntegerField(blank=True, null=True)
    new_displacement_rounded = models.BigIntegerField(blank=True, null=True)
    total_displacement = models.BigIntegerField(blank=True, null=True)
    total_displacement_rounded = models.BigIntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("GIDD Event Displacement")
        verbose_name_plural = _("GIDD Event Displacements")

    def __str__(self):
        return f"{self.event_name} - {self.iso3} - {self.year}"
