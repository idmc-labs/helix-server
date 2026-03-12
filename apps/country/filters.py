import datetime

import django_filters
import graphene
from django.core.exceptions import ValidationError
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
    IDFilter,
    IDListFilter,
    MultiWordSearchFilterSet,
    SimpleInputFilter,
    StringListFilter,
    generate_type_for_filter_set,
)


class HouseholdSizeFilterSet(MultiWordSearchFilterSet):
    filter_idmc_reporting_year = django_filters.NumberFilter(method="filter_reporting_year")
    filter_ahhs_size = django_filters.NumberFilter(method="filter_size")
    filter_ahhs_source = django_filters.CharFilter(method="filter_source")
    filter_ahhs_data_source_category = django_filters.CharFilter(method="filter_source_category")

    def filter_reporting_year(self, qs, name, value):
        if value is None:
            return qs

        return qs.filter(year=value)

    def filter_size(self, qs, name, value):
        if value is None:
            return qs
        return qs.filter(size=value)

    def filter_source(self, qs, name, value):
        if value is None:
            return qs
        return qs.filter(source=value)

    def filter_source_category(self, qs, name, value):
        if value is None:
            return qs
        return qs.filter(data_source_category=value)

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


class CountryFilter(MultiWordSearchFilterSet):
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
        return qs.filter(id__in=Country.objects.filter(events__in=value).values("id"))

    def filter_by_crisis(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(id__in=Country.objects.filter(crises__in=value).values("id"))

    def filter_regions(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(region__in=value).distinct()

    def filter_geo_groups(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(geographical_group__in=value).distinct()

    def filter_year(self, qs, name, value):
        """Filter logic is applied in qs"""
        return qs

    @property
    def qs(self):
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

        return super().qs.annotate(
            **Country._total_figure_disaggregation_subquery(
                figures=figure_qs,
                start_date=start_date,
                end_date=end_date,
            )
        )


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
    HouseholdSizeFilterSet,
    "country.schema.household_size_list",
    "HouseholdSizeFilterDataType",
    "HouseholdSizeFilterDataTypeInputType",
)
