import graphene
import datetime
import django_filters
from django.db.models import Value
from django.utils import timezone
from django.db.models.functions import Lower, StrIndex
from django.core.exceptions import ValidationError
from django.utils.translation import gettext
from django.http import HttpRequest

from apps.country.models import (
    Country,
    CountryRegion,
    GeographicalGroup,
    MonitoringSubRegion,
    ContextualAnalysis,
    Summary,
)
from apps.extraction.filters import (
    FigureExtractionFilterDataInputType,
    FigureExtractionFilterDataType,
)
from utils.filters import (
    IDListFilter,
    StringListFilter,
    NameFilterMixin,
    SimpleInputFilter,
    generate_type_for_filter_set,
)
from utils.figure_filter import (
    FigureFilterHelper,
    CountryFigureAggregateFilterDataType,
    CountryFigureAggregateFilterDataInputType,
)


class GeographicalGroupFilter(NameFilterMixin,
                              django_filters.FilterSet):
    name = django_filters.CharFilter(method='_filter_name')

    class Meta:
        model = GeographicalGroup
        fields = {
            'id': ['iexact'],
        }


class CountryRegionFilter(NameFilterMixin,
                          django_filters.FilterSet):
    name = django_filters.CharFilter(method='_filter_name')

    class Meta:
        model = CountryRegion
        fields = {
            'id': ['iexact'],
        }


class CountryFilter(django_filters.FilterSet):
    country_name = django_filters.CharFilter(method='_filter_name')
    region_name = django_filters.CharFilter(method='filter_region_name')
    geographical_group_name = django_filters.CharFilter(method='filter_geo_group_name')
    region_by_ids = StringListFilter(method='filter_regions')
    geo_group_by_ids = StringListFilter(method='filter_geo_groups')

    filter_figures = SimpleInputFilter(FigureExtractionFilterDataInputType, method='filter_by_figures')
    aggregate_figures = SimpleInputFilter(CountryFigureAggregateFilterDataInputType, method='noop')

    # used in report country table
    events = IDListFilter(method='filter_by_events')
    crises = IDListFilter(method='filter_by_crisis')

    request: HttpRequest

    class Meta:
        model = Country
        fields = {
            'iso3': ['unaccent__icontains'],
            'id': ['iexact'],
        }

    def noop(self, qs, name, value):
        return qs

    def filter_by_figures(self, qs, _, value):
        return FigureFilterHelper.filter_using_figure_filters(qs, value, self.request)

    def filter_by_events(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(
            id__in=Country.objects.filter(events__in=value).values('id')
        )

    def filter_by_crisis(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(
            id__in=Country.objects.filter(crises__in=value).values('id')
        )

    def _filter_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.annotate(
            lname=Lower('idmc_short_name')
        ).annotate(
            idx=StrIndex('lname', Value(value.lower()))
        ).filter(idx__gt=0).order_by('idx', 'idmc_short_name')

    def filter_geo_group_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.select_related(
            'geographical_group'
        ).annotate(
            geo_name=Lower('geographical_group__name')
        ).annotate(
            idx=StrIndex('geo_name', Value(value.lower()))
        ).filter(idx__gt=0).order_by('idx', 'geo_name')

    def filter_region_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.select_related(
            'region'
        ).annotate(
            region_name=Lower('region__name')
        ).annotate(
            idx=StrIndex('region_name', Value(value.lower()))
        ).filter(idx__gt=0).order_by('idx', 'region_name')

    def filter_regions(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(region__in=value).distinct()

    def filter_geo_groups(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(geographical_group__in=value).distinct()

    def filter_year(self, qs, name, value):
        ''' Filter logic is applied in qs'''
        return qs

    @property
    def qs(self):
        # Aggregate filter logic
        aggregate_figures = self.data.get('aggregate_figures') or {}
        year = aggregate_figures.get('year')
        report_id = FigureFilterHelper.get_report_id_from_filter_data(aggregate_figures)
        report = report_id and FigureFilterHelper.get_report(report_id)
        # Only 1 is allowed among report and year
        if report and year:
            raise ValidationError(gettext('Cannot pass both report and year in filter'))

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


class MonitoringSubRegionFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(method='_filter_name')

    class Meta:
        model = MonitoringSubRegion
        fields = ['id']

    def _filter_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.annotate(
            lname=Lower('name')
        ).annotate(
            idx=StrIndex('lname', Value(value.lower()))
        ).filter(idx__gt=0).order_by('idx', 'name')


class CountrySummaryFilter(django_filters.FilterSet):
    class Meta:
        model = Summary
        fields = {
            'created_at': ['lte', 'gte']
        }


class ContextualAnalysisFilter(django_filters.FilterSet):
    class Meta:
        model = ContextualAnalysis
        fields = {
            'created_at': ['lte', 'gte']
        }


CountryFilterDataType, CountryFilterDataInputType = generate_type_for_filter_set(
    CountryFilter,
    'country.schema.country_list',
    'CountryFilterDataType',
    'CountryFilterDataInputType',
    custom_new_fields_map={
        'filter_figures': graphene.Field(FigureExtractionFilterDataType),
        'aggregate_figures': graphene.Field(CountryFigureAggregateFilterDataType),
    },
)
