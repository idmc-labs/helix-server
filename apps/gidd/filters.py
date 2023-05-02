import django_filters
from utils.filters import StringListFilter
from .models import (
    Conflict,
    Disaster,
    StatusLog,
    PublicFigureAnalysis,
    DisplacementData,
    ReleaseMetadata,
)


class ReleaseMetadataFilter(django_filters.FilterSet):
    release_environment = django_filters.CharFilter(method='filter_release_environment', required=True)

    def filter_release_environment(self, qs, name, value):
        release_meta_data = ReleaseMetadata.objects.last()
        if not release_meta_data:
            return qs.filter(year__lte=0)
        elif value == ReleaseMetadata.ReleaseEnvironment.PRE_RELEASE.name:
            return qs.filter(year__lte=release_meta_data.pre_release_year)
        elif value == ReleaseMetadata.ReleaseEnvironment.RELEASE.name:
            return qs.filter(year__lte=release_meta_data.release_year)
        return qs.filter(year__lte=0)


class ConflictFilter(ReleaseMetadataFilter):
    class Meta:
        model = Conflict
        fields = {
            'id': ['iexact']
        }


class DisasterFilter(ReleaseMetadataFilter):
    class Meta:
        model = Disaster
        fields = {
            'id': ['iexact']
        }


class ConflictStatisticsFilter(ReleaseMetadataFilter):
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
        return queryset.filter(iso3__in=value)


class DisasterStatisticsFilter(ReleaseMetadataFilter):
    categories = StringListFilter(method='filter_categories')
    countries = StringListFilter(method='filter_countries')
    start_year = django_filters.NumberFilter(method='filter_start_year')
    end_year = django_filters.NumberFilter(method='filter_end_year')
    countries_iso3 = StringListFilter(method='filter_countries_iso3')

    class Meta:
        model = Disaster
        fields = ()

    def filter_categories(self, queryset, name, value):
        return queryset.filter(hazard_type_name__in=value)

    def filter_countries(self, queryset, name, value):
        return queryset.filter(country__in=value)

    def filter_start_year(self, queryset, name, value):
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        return queryset.filter(year__lte=value)

    def filter_countries_iso3(self, queryset, name, value):
        return queryset.filter(iso3__in=value)


class GiddStatusLogFilter(django_filters.FilterSet):
    status = StringListFilter(method='filter_by_status')

    class Meta:
        model = StatusLog
        fields = ()

    def filter_by_status(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(status__in=value)
            return qs.filter(status__in=[
                StatusLog.Status.get(item).value for item in value
            ])
        return qs


class PublicFigureAnalysisFilter(ReleaseMetadataFilter):
    class Meta:
        model = PublicFigureAnalysis
        fields = {
            'iso3': ['exact'],
            'year': ['exact'],
        }


class DisplacementDataFilter(ReleaseMetadataFilter):
    start_year = django_filters.NumberFilter(method='filter_start_year')
    end_year = django_filters.NumberFilter(method='filter_end_year')
    countries_iso3 = StringListFilter(method='filter_countries_iso3')

    class Meta:
        model = DisplacementData
        fields = ()

    def filter_start_year(self, queryset, name, value):
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        return queryset.filter(year__lte=value)

    def filter_countries_iso3(self, queryset, name, value):
        return queryset.filter(iso3__in=value)
