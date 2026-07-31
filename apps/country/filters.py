import datetime

import django_filters
import graphene
from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext

from apps.country.models import (
    ContextualAnalysis,
    Country,
    CountryRegion,
    GeographicalGroup,
    HouseholdSize,
    MonitoringSubRegion,
    Summary,
)
from apps.extraction.filters import (
    FigureExtractionFilterDataInputType,
    FigureExtractionFilterDataType,
)
from utils.figure_filter import (
    CountryFigureAggregateFilterDataInputType,
    CountryFigureAggregateFilterDataType,
    FigureFilterHelper,
)
from utils.filters import (
    AcceptsOrdering,
    IDFilter,
    IDListFilter,
    MultiWordSearchFilterSet,
    SimpleInputFilter,
    StringListFilter,
    generate_type_for_filter_set,
)


class HouseholdSizeFilter(MultiWordSearchFilterSet):
    year = django_filters.NumberFilter(method="filter_year")
    ahhs_source = django_filters.CharFilter(method="filter_source")
    countries = IDListFilter(method="filter_countries")

    def filter_year(self, qs, name, value):
        if value is None:
            return qs

        return qs.filter(year=value)

    def filter_source(self, qs, name, value):
        if value is None:
            return qs
        return qs.filter(source=value)

    def filter_countries(self, qs, name, value):
        if value is None:
            return qs
        return qs.filter(country__in=value)

    @property
    def qs(self):
        return super().qs.filter(is_active=True)

    class Meta:
        model = HouseholdSize
        fields = []
        multi_word_search_fields = ["country__name", "data_source_category", "notes"]


class GeographicalGroupFilter(MultiWordSearchFilterSet):
    id = IDFilter(field_name="id", lookup_expr="exact")

    class Meta:
        model = GeographicalGroup
        fields = []
        multi_word_search_fields = ["name"]


class CountryRegionFilter(MultiWordSearchFilterSet):
    id = IDFilter(field_name="id", lookup_expr="exact")

    class Meta:
        model = CountryRegion
        fields = []
        multi_word_search_fields = ["name"]


class CountryFilter(AcceptsOrdering, MultiWordSearchFilterSet):
    id = IDFilter(field_name="id", lookup_expr="exact")
    region_by_ids = StringListFilter(method="filter_regions")
    geo_group_by_ids = StringListFilter(method="filter_geo_groups")

    filter_figures = SimpleInputFilter(FigureExtractionFilterDataInputType, method="filter_by_figures")
    aggregate_figures = SimpleInputFilter(CountryFigureAggregateFilterDataInputType, method="noop")

    # used in report country table
    events = IDListFilter(method="filter_by_events")
    crises = IDListFilter(method="filter_by_crisis")

    request: HttpRequest

    class Meta:
        model = Country
        fields = []
        multi_word_search_fields = ["idmc_short_name", "iso3"]

    def noop(self, qs, name, value):
        return qs

    def filter_by_figures(self, qs, _, value):
        return FigureFilterHelper.filter_using_figure_filters(qs, value, self.request)

    def filter_by_events(self, qs, name, value):
        if not value:
            return qs
        # Correlated Exists over the event<->country M2M through table (mirrors the
        # Exists-over-distinct conversion elsewhere); the through model is reached via _meta
        # to avoid importing Event here.
        through = Country._meta.get_field("events").through
        return qs.filter(Exists(through.objects.filter(country_id=OuterRef("pk"), event_id__in=value)))

    def filter_by_crisis(self, qs, name, value):
        if not value:
            return qs
        through = Country._meta.get_field("crises").through
        return qs.filter(Exists(through.objects.filter(country_id=OuterRef("pk"), crisis_id__in=value)))

    def filter_regions(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(region__in=value)

    def filter_geo_groups(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(geographical_group__in=value)

    def filter_year(self, qs, name, value):
        """Filter logic is applied in qs"""
        return qs

    @property
    def qs(self):
        queryset = super().qs

        # Aggregate filter logic
        aggregate_figures = self.data.get("aggregate_figures") or {}
        year = aggregate_figures.get("year")
        report_id = FigureFilterHelper.get_report_id_from_filter_data(aggregate_figures)
        report = report_id and FigureFilterHelper.get_report(report_id)
        # Only 1 is allowed among report and year
        if report and year:
            raise ValidationError(gettext("Cannot pass both report and year in filter"))

        start_date = None
        figure_qs, end_date = FigureFilterHelper.aggregate_data_generate(aggregate_figures, self.request)
        if end_date is None:
            year = year or timezone.now().year
            start_date = datetime.datetime(year=int(year), month=1, day=1)
            end_date = datetime.datetime(year=int(year), month=12, day=31)

        # nd/idp totals are annotated only when needed: aggregate_figures set, or sorting by them
        # (else resolvers read the default current-year dataloaders). Both cases use the set-based
        # CTE — one grouped scan over the figures grouped by country. aggregate_figures passes its
        # filtered figure_qs + date range (scoped totals); the sort path uses the default scope.
        # This replaces four per-country correlated subqueries re-scanned once per page row
        # (444ms -> 60ms on a 50-row page). Gate on the raw field, not figure_qs: a year-only
        # filter leaves figure_qs None but still needs its own date range.
        figure_count_sort_fields = {
            Country.ND_CONFLICT_ANNOTATE,
            Country.ND_DISASTER_ANNOTATE,
            Country.IDP_CONFLICT_ANNOTATE,
            Country.IDP_DISASTER_ANNOTATE,
        }
        if aggregate_figures:
            queryset = Country.annotate_total_figure_disaggregation_via_cte(
                queryset, figures=figure_qs, start_date=start_date, end_date=end_date
            )
        elif self.ordering_fields & figure_count_sort_fields:
            queryset = Country.annotate_total_figure_disaggregation_via_cte(queryset)

        return queryset


class MonitoringSubRegionFilter(MultiWordSearchFilterSet):
    id = IDFilter(field_name="id", lookup_expr="exact")
    name = django_filters.CharFilter(method="_filter_name")

    class Meta:
        model = MonitoringSubRegion
        fields = []
        multi_word_search_fields = ["name"]


class CountrySummaryFilter(django_filters.FilterSet):
    class Meta:
        model = Summary
        fields = {"created_at": ["lte", "gte"]}


class ContextualAnalysisFilter(django_filters.FilterSet):
    class Meta:
        model = ContextualAnalysis
        fields = {"created_at": ["lte", "gte"]}


CountryFilterDataType, CountryFilterDataInputType = generate_type_for_filter_set(
    CountryFilter,
    "country.schema.country_list",
    "CountryFilterDataType",
    "CountryFilterDataInputType",
    custom_new_fields_map={
        "filter_figures": graphene.Field(FigureExtractionFilterDataType),
        "aggregate_figures": graphene.Field(CountryFigureAggregateFilterDataType),
    },
)


MonitoringSubRegionFilterDataType, MonitoringSubRegionFilterDataInputType = generate_type_for_filter_set(
    MonitoringSubRegionFilter,
    "country.schema.monitoring_sub_region_list",
    "MonitoringSubRegionFilterDataType",
    "MonitoringSubRegionFilterDataInputType",
)

HouseholdSizeFilterDataType, HouseholdSizeFilterDataTypeInputType = generate_type_for_filter_set(
    HouseholdSizeFilter,
    "country.schema.household_size_list",
    "HouseholdSizeFilterDataType",
    "HouseholdSizeFilterDataTypeInputType",
)
