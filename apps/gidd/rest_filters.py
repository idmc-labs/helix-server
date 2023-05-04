import django_filters
from .filters import ReleaseMetadataFilter
from .models import (
    Conflict,
    Disaster,
    DisplacementData,
)


class RestConflictFilterSet(ReleaseMetadataFilter):
    start_year = django_filters.NumberFilter(field_name='start_year', method='filter_start_year')
    end_year = django_filters.NumberFilter(field_name='end_year', method='filter_end_year')

    class Meta:
        model = Conflict
        fields = {
            'id': ['iexact'],
            'iso3': ['iexact'],
            'year': ['iexact'],
        }

    def filter_start_year(self, queryset, name, value):
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        return queryset.filter(year__lte=value)


class RestDisasterFilterSet(ReleaseMetadataFilter):
    start_year = django_filters.NumberFilter(field_name='start_year', method='filter_start_year')
    end_year = django_filters.NumberFilter(field_name='end_year', method='filter_end_year')

    class Meta:
        model = Disaster
        fields = {
            'id': ['iexact'],
            'iso3': ['in'],
            'hazard_type': ['in'],
        }

    def filter_start_year(self, queryset, name, value):
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        return queryset.filter(year__lte=value)


class RestDisplacementDataFilterSet(ReleaseMetadataFilter):
    start_year = django_filters.NumberFilter(field_name='start_year', method='filter_start_year')
    end_year = django_filters.NumberFilter(field_name='end_year', method='filter_end_year')
    is_conflict = django_filters.BooleanFilter(method='filter_is_conflict')
    is_disaster = django_filters.BooleanFilter(method='filter_is_disaster')

    class Meta:
        model = DisplacementData
        fields = ()

    def filter_start_year(self, queryset, name, value):
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        return queryset.filter(year__lte=value)

    def filter_is_conflict(self, queryset, name, value):
        return queryset.filter(
            conflict_total_displacement__isnull=False,
            conflict_new_displacement__isnull=False
        )

    def filter_is_disaster(self, queryset, name, value):
        return queryset.filter(
            disaster_total_displacement__isnull=False,
            disaster_new_displacement__isnull=False
        )
