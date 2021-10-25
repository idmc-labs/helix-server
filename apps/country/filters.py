import django_filters
from datetime import datetime
from django.utils import timezone
from django.db.models import (
    Value,
)
from django.db.models.functions import Lower, StrIndex

from apps.country.models import (
    Country,
    CountryRegion,
    GeographicalGroup,
    MonitoringSubRegion,
)
from apps.report.models import Report
from utils.filters import StringListFilter, NameFilterMixin


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

    # used in report country table
    report = django_filters.CharFilter(method='filter_report')
    year = django_filters.NumberFilter(method='filter_year')

    class Meta:
        model = Country
        fields = {
            'iso3': ['unaccent__icontains'],
            'id': ['iexact'],
        }

    def filter_report(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(
            id__in=Report.objects.get(id=value).report_figures.values('country')
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
        year = self.data.get('year', timezone.now().year)
        start_date, end_date = None, None
        if year:
            year_int = int(year)
            start_date = datetime(year=year_int, month=1, day=1)
            end_date = datetime(year=year_int, month=12, day=31)

        qs = super().qs.annotate(
            **Country._total_figure_disaggregation_subquery(
                start_date=start_date, end_date=end_date
            )
        )
        return qs


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
