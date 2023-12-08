from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationAbstractModel
from apps.entry.models import (
    Figure,
)
from apps.crisis.models import Crisis
from apps.entry.constants import STOCK, FLOW


class QueryAbstractModel(models.Model):
    filter_figure_geographical_groups = models.ManyToManyField(
        'country.GeographicalGroup',
        verbose_name=_('Geographical Group'),
        blank=True,
        related_name='+'
    )
    filter_figure_regions = models.ManyToManyField(
        'country.CountryRegion',
        verbose_name=_('Regions'),
        blank=True,
        related_name='+'
    )
    filter_figure_countries = models.ManyToManyField(
        'country.Country',
        verbose_name=_('Countries'),
        blank=True,
        related_name='+'
    )
    filter_figure_events = models.ManyToManyField(
        'event.Event',
        verbose_name=_('Events'),
        blank=True,
    )
    filter_figure_crises = models.ManyToManyField(
        'crisis.Crisis',
        verbose_name=_('Crises'),
        blank=True,
        related_name='+'
    )
    filter_figure_categories = ArrayField(
        base_field=enum.EnumField(enum=Figure.FIGURE_CATEGORY_TYPES),
        null=True,
        blank=True,
    )
    filter_figure_sources = models.ManyToManyField(
        'organization.Organization',
        verbose_name=_('Sources'),
        related_name='sourced_%(class)s',
        blank=True
    )
    filter_entry_publishers = models.ManyToManyField(
        'organization.Organization',
        verbose_name=_('Publishers'),
        related_name='published_%(class)s',
        blank=True
    )
    filter_figure_start_after = models.DateField(
        verbose_name=_('From Date'),
        blank=True,
        null=True
    )
    filter_figure_end_before = models.DateField(
        verbose_name=_('To Date'),
        blank=True,
        null=True
    )
    filter_figure_roles = ArrayField(
        base_field=enum.EnumField(enum=Figure.ROLE),
        blank=True,
        null=True
    )
    filter_figure_tags = models.ManyToManyField(
        'entry.FigureTag',
        verbose_name=_('Figure Tags'),
        blank=True,
        related_name='+'
    )
    filter_entry_article_title = models.TextField(
        verbose_name=_('Event Title'),
        blank=True,
        null=True
    )
    filter_figure_crisis_types = ArrayField(
        base_field=enum.EnumField(enum=Crisis.CRISIS_TYPE),
        blank=True,
        null=True
    )
    filter_figure_glide_number = ArrayField(
        base_field=models.CharField(verbose_name=_('Event Code'), max_length=100, null=True),
        blank=True,
        null=True
    )
    filter_figure_created_by = models.ManyToManyField(
        'users.User',
        verbose_name=_('Figure Created by'),
        blank=True,
    )
    filter_figure_approved_by = models.ManyToManyField(
        'users.User',
        verbose_name=_('Figure Approved by'),
        related_name='+',
        blank=True,
    )
    filter_figure_terms = ArrayField(
        base_field=enum.EnumField(enum=Figure.FIGURE_TERMS),
        blank=True,
        null=True
    )
    filter_figure_review_status = ArrayField(
        base_field=enum.EnumField(enum=Figure.FIGURE_REVIEW_STATUS),
        blank=True,
        null=True
    )
    filter_figure_disaster_categories = models.ManyToManyField(
        'event.DisasterCategory',
        verbose_name=_('Hazard Category'),
        blank=True,
    )
    filter_figure_disaster_sub_categories = models.ManyToManyField(
        'event.DisasterSubCategory',
        verbose_name=_('Hazard Sub Category'),
        blank=True,
    )
    filter_figure_disaster_types = models.ManyToManyField(
        'event.DisasterType',
        verbose_name=_('Hazard Type'),
        blank=True,
    )
    filter_figure_disaster_sub_types = models.ManyToManyField(
        'event.DisasterSubType',
        verbose_name=_('Hazard Sub Type'),
        blank=True,
    )
    filter_figure_violence_types = models.ManyToManyField(
        'event.Violence',
        verbose_name=_('Violence Type'),
        blank=True,
    )
    filter_figure_violence_sub_types = models.ManyToManyField(
        'event.ViolenceSubType',
        verbose_name=_('Violence Sub Type'),
        blank=True,
    )
    filter_figure_osv_sub_types = models.ManyToManyField(
        'event.OsvSubType',
        verbose_name=_('Osv Sub Type'),
        blank=True,
    )
    filter_figure_category_types = ArrayField(
        base_field=models.CharField(verbose_name=_('Type'), max_length=8, choices=(
            (STOCK, STOCK),
            (FLOW, FLOW),
        ), null=True, blank=True), null=True, blank=True,
    )
    filter_figure_has_disaggregated_data = models.BooleanField(
        verbose_name=_('Has disaggregated data'),
        null=True,
        default=None,
    )
    filter_figure_context_of_violence = models.ManyToManyField(
        'event.ContextOfViolence',
        verbose_name=_('Context of violence'),
        blank=True,
    )
    filter_figure_is_to_be_reviewed = models.BooleanField(
        verbose_name=_('Filter to be reviewed'),
        null=True,
        default=None,
    )
    filter_figure_has_excerpt_idu = models.BooleanField(
        verbose_name=_('Has excerpt IDU'),
        null=True,
        default=None,
    )
    filter_figure_has_housing_destruction = models.BooleanField(
        verbose_name=_('Has housing destruction'),
        null=True,
        default=None,
    )

    @property
    def get_filter_kwargs(self):
        return dict(
            filter_figure_countries=self.filter_figure_countries.all(),
            filter_figure_regions=self.filter_figure_regions.all(),
            filter_figure_geographical_groups=self.filter_figure_geographical_groups.all(),
            filter_figure_events=self.filter_figure_events.all(),
            filter_figure_crises=self.filter_figure_crises.all(),
            filter_figure_categories=self.filter_figure_categories,
            filter_figure_tags=self.filter_figure_tags.all(),
            filter_figure_roles=self.filter_figure_roles,
            filter_figure_start_after=self.filter_figure_start_after,
            filter_figure_end_before=self.filter_figure_end_before,
            filter_entry_article_title=self.filter_entry_article_title,
            filter_figure_crisis_types=self.filter_figure_crisis_types,
            filter_figure_terms=self.filter_figure_terms,
            filter_figure_disaster_categories=self.filter_figure_disaster_categories.all(),
            filter_figure_disaster_sub_categories=self.filter_figure_disaster_sub_categories.all(),
            filter_figure_disaster_types=self.filter_figure_disaster_types.all(),
            filter_figure_disaster_sub_types=self.filter_figure_disaster_sub_types.all(),
            filter_figure_violence_types=self.filter_figure_violence_types.all(),
            filter_figure_violence_sub_types=self.filter_figure_violence_sub_types.all(),
            filter_figure_osv_sub_types=self.filter_figure_osv_sub_types.all(),
            filter_figure_category_types=self.filter_figure_category_types,
            filter_figure_has_disaggregated_data=self.filter_figure_has_disaggregated_data,
            filter_figure_context_of_violence=self.filter_figure_context_of_violence.all(),
            filter_figure_is_to_be_reviewed=self.filter_figure_is_to_be_reviewed,
            filter_figure_approved_by=self.filter_figure_approved_by.all(),
            filter_figure_glide_number=self.filter_figure_glide_number,
            filter_figure_created_by=self.filter_figure_created_by.all(),
            filter_figure_sources=self.filter_figure_sources.all(),
            filter_entry_publishers=self.filter_entry_publishers.all(),
            filter_figure_review_status=self.filter_figure_review_status,
            filter_figure_has_excerpt_idu=self.filter_figure_has_excerpt_idu,
            filter_figure_has_housing_destruction=self.filter_figure_has_housing_destruction,
        )

    @property
    def extract_figures(self) -> ['Figure']:  # noqa
        from apps.extraction.filters import FigureExtractionFilterSet
        return FigureExtractionFilterSet(data=self.get_filter_kwargs).qs

    # FIXME: we may not need this anymore
    @property
    def extract_report_figures(self) -> ['Figure']:  # noqa
        """
        Use this method in report only
        """
        from apps.extraction.filters import ReportFigureExtractionFilterSet
        return ReportFigureExtractionFilterSet(data=self.get_filter_kwargs).qs

    @classmethod
    def get_entries(cls, data=None) -> ['Entry']:  # noqa
        from apps.extraction.filters import EntryExtractionFilterSet
        return EntryExtractionFilterSet(data=data).qs

    @property
    def entries(self) -> ['Entry']:  # noqa
        return self.get_entries(data=self.get_filter_kwargs)

    class Meta:
        abstract = True


class ExtractionQuery(MetaInformationAbstractModel, QueryAbstractModel):
    name = models.CharField(
        verbose_name=_('Name'),
        max_length=128
    )
