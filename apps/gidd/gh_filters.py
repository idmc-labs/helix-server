import django_filters

from utils.filters import StringListFilter
from .models import (
    Conflict,
    Disaster,
)


class ConflictFilter(django_filters.FilterSet):
    class Meta:
        model = Conflict
        fields = {
            'id': ['iexact']
        }


class DisasterFilter(django_filters.FilterSet):
    class Meta:
        model = Disaster
        fields = {
            'id': ['iexact']
        }


class ConflictStatisticsFilter(django_filters.FilterSet):
    countries = StringListFilter(method='filter_countries')
    start_year = django_filters.NumberFilter(method='filter_start_year')
    end_year = django_filters.NumberFilter(method='filter_end_year')
    countries_iso3 = StringListFilter(method='filter_countries_iso3')

    class Meta:
        model = Conflict
        fields = ()

    def filter_countries(self, queryset, name, value):
        return queryset.filter(country__in=value)

    def filter_start_year(self, queryset, name, value):
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        return queryset.filter(year__lte=value)

    def filter_countries_iso3(self, queryset, name, value):
        return queryset.filter(country__iso3__in=value)


class DisasterStatisticsFilter(django_filters.FilterSet):
    categories = StringListFilter(method='filter_categories')
    countries = StringListFilter(method='filter_countries')
    start_year = django_filters.NumberFilter(method='filter_end_year')
    end_year = django_filters.NumberFilter(method='filter_end_year')
    countries_iso3 = StringListFilter(method='filter_countries_iso3')

    class Meta:
        model = Disaster
        fields = ()

    def filter_categories(self, queryset, name, value):
        return queryset.filter(hazard_type__in=value)

    def filter_countries(self, queryset, name, value):
        return queryset.filter(country__in=value)

    def filter_start_year(self, queryset, name, value):
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        return queryset.filter(year__lte=value)

    def filter_countries_iso3(self, queryset, name, value):
        return queryset.filter(country__iso3__in=value)
