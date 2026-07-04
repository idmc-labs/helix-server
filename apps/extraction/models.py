from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationAbstractModel
from apps.crisis.models import Crisis
from apps.entry.constants import FLOW, STOCK
from apps.entry.models import (
    Figure,
)


class QueryAbstractModel(models.Model):
    filter_figure_geographical_groups = models.ManyToManyField(
        "country.GeographicalGroup", verbose_name=_("Geographical Group"), blank=True, related_name="+"
    )
    filter_figure_regions = models.ManyToManyField(
        "country.CountryRegion", verbose_name=_("Regions"), blank=True, related_name="+"
    )
    filter_figure_countries = models.ManyToManyField(
        "country.Country", verbose_name=_("Countries"), blank=True, related_name="+"
    )
    filter_figure_events = models.ManyToManyField(
        "event.Event",
        verbose_name=_("Events"),
        blank=True,
    )
    filter_figure_crises = models.ManyToManyField("crisis.Crisis", verbose_name=_("Crises"), blank=True, related_name="+")
    filter_figure_categories = ArrayField(
        base_field=enum.EnumField(enum=Figure.FIGURE_CATEGORY_TYPES),
        null=True,
        blank=True,
    )
    filter_figure_sources = models.ManyToManyField(
        "organization.Organization", verbose_name=_("Sources"), related_name="sourced_%(class)s", blank=True
    )
    filter_entry_publishers = models.ManyToManyField(
        "organization.Organization", verbose_name=_("Publishers"), related_name="published_%(class)s", blank=True
    )
    filter_figure_start_after = models.DateField(verbose_name=_("From Date"), blank=True, null=True)
    filter_figure_end_before = models.DateField(verbose_name=_("To Date"), blank=True, null=True)
    filter_figure_roles = ArrayField(base_field=enum.EnumField(enum=Figure.ROLE), blank=True, null=True)
    filter_figure_tags = models.ManyToManyField(
        "entry.FigureTag", verbose_name=_("Figure Tags"), blank=True, related_name="+"
    )
    filter_entry_article_title = models.TextField(verbose_name=_("Event Title"), blank=True, null=True)
    filter_figure_crisis_types = ArrayField(base_field=enum.EnumField(enum=Crisis.CRISIS_TYPE), blank=True, null=True)
    filter_figure_glide_number = ArrayField(
        base_field=models.CharField(verbose_name=_("Event Code"), max_length=100, null=True), blank=True, null=True
    )
    filter_figure_created_by = models.ManyToManyField(
        "users.User",
        verbose_name=_("Figure Created by"),
        blank=True,
    )
    filter_figure_approved_by = models.ManyToManyField(
        "users.User",
        verbose_name=_("Figure Approved by"),
        related_name="+",
        blank=True,
    )
    filter_figure_terms = ArrayField(base_field=enum.EnumField(enum=Figure.FIGURE_TERMS), blank=True, null=True)
    filter_figure_review_status = ArrayField(
        base_field=enum.EnumField(enum=Figure.FIGURE_REVIEW_STATUS), blank=True, null=True
    )
    filter_figure_disaster_categories = models.ManyToManyField(
        "event.DisasterCategory",
        verbose_name=_("Hazard Category"),
        blank=True,
    )
    filter_figure_disaster_sub_categories = models.ManyToManyField(
        "event.DisasterSubCategory",
        verbose_name=_("Hazard Sub Category"),
        blank=True,
    )
    filter_figure_disaster_types = models.ManyToManyField(
        "event.DisasterType",
        verbose_name=_("Hazard Type"),
        blank=True,
    )
    filter_figure_disaster_sub_types = models.ManyToManyField(
        "event.DisasterSubType",
        verbose_name=_("Hazard Sub Type"),
        blank=True,
    )
    filter_figure_violence_types = models.ManyToManyField(
        "event.Violence",
        verbose_name=_("Violence Type"),
        blank=True,
    )
    filter_figure_violence_sub_types = models.ManyToManyField(
        "event.ViolenceSubType",
        verbose_name=_("Violence Sub Type"),
        blank=True,
    )
    filter_figure_osv_sub_types = models.ManyToManyField(
        "event.OsvSubType",
        verbose_name=_("Osv Sub Type"),
        blank=True,
    )
    filter_figure_category_types = ArrayField(
        base_field=models.CharField(
            verbose_name=_("Type"),
            max_length=8,
            choices=(
                (STOCK, STOCK),
                (FLOW, FLOW),
            ),
            null=True,
            blank=True,
        ),
        null=True,
        blank=True,
    )
    filter_figure_has_disaggregated_data = models.BooleanField(
        verbose_name=_("Has disaggregated data"),
        null=True,
        default=None,
    )
    filter_figure_context_of_violence = models.ManyToManyField(
        "event.ContextOfViolence",
        verbose_name=_("Context of violence"),
        blank=True,
    )
    filter_figure_is_to_be_reviewed = models.BooleanField(
        verbose_name=_("Filter to be reviewed"),
        null=True,
        default=None,
    )
    filter_figure_has_excerpt_idu = models.BooleanField(
        verbose_name=_("Has excerpt IDU"),
        null=True,
        default=None,
    )
    filter_figure_has_housing_destruction = models.BooleanField(
        verbose_name=_("Has housing destruction"),
        null=True,
        default=None,
    )

    # Bounded staleness window for the cached filter kwargs. Every live edit path
    # (serializer/admin) saves the instance first (auto_now bumps modified_at), so the
    # cache key rotates on edit and the TTL only matters for out-of-band writes
    # (e.g. a data migration touching the filter M2Ms directly).
    FILTER_KWARGS_CACHE_TTL = 6 * 60 * 60

    @property
    def get_filter_kwargs(self):
        # The stored filter definition only changes when the instance is edited, but
        # reading it costs one query per M2M filter field (~18) — a fixed tax on every
        # report-scoped list/figure query. Cache the computed kwargs keyed on
        # (model, pk, modified_at): a save rotates modified_at, so edits invalidate
        # by construction. (Prefetching instead was measured as a regression — there
        # is no N to amortize on the single-report path.)
        if self.pk is None:
            return self._compute_filter_kwargs()
        modified_at = getattr(self, "modified_at", None)  # from the MetaInformation mixins
        stamp = modified_at.isoformat() if modified_at else "na"
        key = f"query_filter_kwargs:v1:{self._meta.label_lower}:{self.pk}:{stamp}"
        data = cache.get(key)
        if data is None:
            data = self._compute_filter_kwargs()
            cache.set(key, data, self.FILTER_KWARGS_CACHE_TTL)
        return data

    def _compute_filter_kwargs(self):
        # NOTE: M2M filter values are read as id lists (values_list) rather than
        # full model instances. The figure filterset only needs the ids (it filters
        # with `__in`), so this avoids materializing fat rows (e.g. country geometry,
        # full event/crisis/organization records) just to check/apply each filter.
        #
        # If the relation was prefetched (e.g. ReportTotalDisaggregationLoader prefetches
        # all filter M2Ms with .only("id") to batch a report list), read the ids from the
        # prefetch cache instead — values_list() would ignore the cache and re-query per
        # relation per report (the N+1 this avoids). Falls back to the lean values_list
        # when not prefetched (the single-report figureList path is unchanged).
        prefetched = getattr(self, "_prefetched_objects_cache", {})

        def ids(manager):
            if getattr(manager, "prefetch_cache_name", None) in prefetched:
                return [obj.pk for obj in manager.all()]
            return list(manager.values_list("id", flat=True))

        return dict(
            filter_figure_countries=ids(self.filter_figure_countries),
            filter_figure_regions=ids(self.filter_figure_regions),
            filter_figure_geographical_groups=ids(self.filter_figure_geographical_groups),
            filter_figure_events=ids(self.filter_figure_events),
            filter_figure_crises=ids(self.filter_figure_crises),
            filter_figure_categories=self.filter_figure_categories,
            filter_figure_tags=ids(self.filter_figure_tags),
            filter_figure_roles=self.filter_figure_roles,
            filter_figure_start_after=self.filter_figure_start_after,
            filter_figure_end_before=self.filter_figure_end_before,
            filter_entry_article_title=self.filter_entry_article_title,
            filter_figure_crisis_types=self.filter_figure_crisis_types,
            filter_figure_terms=self.filter_figure_terms,
            filter_figure_disaster_categories=ids(self.filter_figure_disaster_categories),
            filter_figure_disaster_sub_categories=ids(self.filter_figure_disaster_sub_categories),
            filter_figure_disaster_types=ids(self.filter_figure_disaster_types),
            filter_figure_disaster_sub_types=ids(self.filter_figure_disaster_sub_types),
            filter_figure_violence_types=ids(self.filter_figure_violence_types),
            filter_figure_violence_sub_types=ids(self.filter_figure_violence_sub_types),
            filter_figure_osv_sub_types=ids(self.filter_figure_osv_sub_types),
            filter_figure_category_types=self.filter_figure_category_types,
            filter_figure_has_disaggregated_data=self.filter_figure_has_disaggregated_data,
            filter_figure_context_of_violence=ids(self.filter_figure_context_of_violence),
            filter_figure_is_to_be_reviewed=self.filter_figure_is_to_be_reviewed,
            filter_figure_approved_by=ids(self.filter_figure_approved_by),
            filter_figure_glide_number=self.filter_figure_glide_number,
            filter_figure_created_by=ids(self.filter_figure_created_by),
            filter_figure_sources=ids(self.filter_figure_sources),
            filter_entry_publishers=ids(self.filter_entry_publishers),
            filter_figure_review_status=self.filter_figure_review_status,
            filter_figure_has_excerpt_idu=self.filter_figure_has_excerpt_idu,
            filter_figure_has_housing_destruction=self.filter_figure_has_housing_destruction,
        )

    # FIXME: we may not need this anymore
    @property
    def extract_report_figures(self) -> ["Figure"]:  # noqa
        """
        Use this method in report only
        """
        from apps.extraction.filters import ReportFigureExtractionFilterSet

        return ReportFigureExtractionFilterSet(data=self.get_filter_kwargs).qs

    @classmethod
    def get_entries(cls, data=None) -> ["Entry"]:  # noqa
        from apps.extraction.filters import EntryExtractionFilterSet

        return EntryExtractionFilterSet(data=data).qs

    @property
    def entries(self) -> ["Entry"]:  # noqa
        return self.get_entries(data=self.get_filter_kwargs)

    class Meta:
        abstract = True


class ExtractionQuery(MetaInformationAbstractModel, QueryAbstractModel):
    name = models.CharField(verbose_name=_("Name"), max_length=128)
