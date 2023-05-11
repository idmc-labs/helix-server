import django_filters
from django.db.models import Q
from .filters import ReleaseMetadataFilter
from .models import (
    Conflict,
    Disaster,
    DisplacementData,
    IdpsSaddEstimate,
)
from apps.crisis.models import Crisis


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

    @property
    def qs(self):
        qs = super().qs
        return qs.filter(new_displacement__gt=0)


class RestDisplacementDataFilterSet(ReleaseMetadataFilter):
    start_year = django_filters.NumberFilter(field_name='start_year', method='filter_start_year')
    end_year = django_filters.NumberFilter(field_name='end_year', method='filter_end_year')
    cause = django_filters.CharFilter(method='filter_cause')

    class Meta:
        model = DisplacementData
        fields = {
            'iso3': ['in'],
        }

    def filter_start_year(self, queryset, name, value):
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        return queryset.filter(year__lte=value)

    def filter_cause(self, queryset, name, value):
        if value == 'conflict':
            return queryset.filter(
                Q(conflict_new_displacement__gt=0) |
                Q(conflict_total_displacement__gt=0)
            )
        elif value == 'disaster':
            return queryset.filter(
                Q(disaster_new_displacement__gt=0) |
                Q(disaster_total_displacement__gt=0)
            )

    @property
    def qs(self):
        qs = super().qs
        if 'cause' not in self.data:
            return qs.filter(
                Q(conflict_new_displacement__gt=0) |
                Q(conflict_total_displacement__gt=0) |
                Q(disaster_new_displacement__gt=0) |
                Q(disaster_total_displacement__gt=0)
            )
        return qs


class IdpsSaddEstimateFilter(ReleaseMetadataFilter):
    start_year = django_filters.NumberFilter(field_name='start_year', method='filter_start_year')
    end_year = django_filters.NumberFilter(field_name='end_year', method='filter_end_year')
    cause = django_filters.CharFilter(method='filter_cause')

    class Meta:
        model = IdpsSaddEstimate
        fields = {
            'iso3': ['in'],
        }

    def filter_start_year(self, queryset, name, value):
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        return queryset.filter(year__lte=value)

    def filter_cause(self, queryset, name, value):
        # NOTE: this filter is used inside displacement export
        if value == 'conflict':
            return queryset.filter(
                cause=Crisis.CRISIS_TYPE.CONFLICT.value,
            )

        elif value == 'disaster':
            return queryset.filter(
                cause=Crisis.CRISIS_TYPE.DISASTER.value,
            )
        return queryset
