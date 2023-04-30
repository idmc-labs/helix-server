import django_filters
from utils.filters import StringListFilter, IDListFilter
from .models import (
    Conflict,
    Disaster,
    StatusLog,
    PublicFigureAnalysis,
    DisplacementData,
    ReleaseMetadata,
)


class ReleaseMetadataFilter(django_filters.FilterSet):
    release_environment = django_filters.CharFilter(method='filter_release_environment')

    def filter_release_environment(self, qs, name, value):
        release_meta_data = ReleaseMetadata.objects.last()
        if value == ReleaseMetadata.ReleaseEnvironment.STAGING.name:
            return qs.filter(year__lte=release_meta_data.staging_year)
        elif value == ReleaseMetadata.ReleaseEnvironment.PRODUCTION.name:
            return qs.filter(year__lte=release_meta_data.production_year)
        return qs


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
    hazard_sub_types = IDListFilter(method='filter_hazard_sub_types')

    class Meta:
        model = DisplacementData
        fields = ()

    def filter_start_year(self, queryset, name, value):
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        return queryset.filter(year__lte=value)

    def filter_countries_iso3(self, queryset, name, value):
        return queryset.filter(iso3__in=value)

    def filter_hazard_sub_types(self, queryset, name, value):
        return queryset.filter(disasters__hazard_sub_type__in=value,)

    @property
    def qs(self):
        hazard_sub_types = self.data.get('hazard_sub_types', [])
        hazard_filter = {'hazard_sub_type__in': hazard_sub_types}
        return super().qs.annotate(
            **DisplacementData.annotate_disaster_nd(hazard_filter=hazard_filter),
            **DisplacementData.annotate_disaster_idps(hazard_filter=hazard_filter),
        )
