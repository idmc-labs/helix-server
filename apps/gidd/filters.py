import typing

import django_filters
from django.db.models import Q
from rest_framework import serializers

from apps.crisis.models import Crisis
from apps.entry.models import ExternalApiDump
from utils.filters import IDListFilter, MultiWordSearchFilterSet, StringListFilter

from .enums import CRISIS_TYPE_PUBLIC
from .models import (
    Conflict,
    Disaster,
    DisplacementData,
    PublicFigureAnalysis,
    ReleaseMetadata,
    StatusLog,
)


def get_name_choices(enum_class) -> typing.List[typing.Tuple[str, str]]:
    return [(i.name, i.label) for i in enum_class] + [(i.name.lower(), i.label) for i in enum_class]


class ReleaseMetadataFilter(django_filters.FilterSet):
    release_environment = django_filters.ChoiceFilter(
        method="no_op",
        choices=get_name_choices(ReleaseMetadata.ReleaseEnvironment),
    )

    CUSTOM_HELP_TEXT = {"iso3": "Filter by ISO 3166-1 alpha-3 code"}

    @classmethod
    def filter_for_field(cls, f, name, lookup_expr):
        filter = super().filter_for_field(f, name, lookup_expr)
        if custom_help_text := cls.CUSTOM_HELP_TEXT.get(f.name, None):
            filter.extra["help_text"] = custom_help_text
        return filter

    def no_op(self, qs, name, value):
        return qs

    def get_release_metadata(self):
        release_meta_data = ReleaseMetadata.objects.last()
        if not release_meta_data:
            raise serializers.ValidationError("Release metadata is not configured.")
        return release_meta_data

    def filter_release_environment(self, qs, value):
        release_meta_data = self.get_release_metadata()
        if value.lower() == ReleaseMetadata.ReleaseEnvironment.PRE_RELEASE.name.lower():
            return qs.filter(year__lte=release_meta_data.pre_release_year)
        return qs.filter(year__lte=release_meta_data.release_year)

    @property
    def qs(self):
        qs = super().qs
        release_environment_name = self.data.get(
            "release_environment",
            ReleaseMetadata.ReleaseEnvironment.RELEASE.name,
        )
        qs = self.filter_release_environment(qs, release_environment_name)
        return qs


class ConflictFilter(ReleaseMetadataFilter):
    class Meta:
        model = Conflict
        fields = {"id": ["iexact"]}


# FIXME: We cannot update this API filter. This is external
class DisasterFilter(ReleaseMetadataFilter, MultiWordSearchFilterSet):
    hazard_types = IDListFilter(method="filter_hazard_types")
    start_year = django_filters.NumberFilter(method="filter_start_year")
    end_year = django_filters.NumberFilter(method="filter_end_year")
    countries_iso3 = StringListFilter(method="filter_countries_iso3")

    class Meta:
        model = Disaster
        fields = {"id": ["iexact"]}

    @property
    def searchable_fields(self):
        return ["event_name"]

    def filter_hazard_types(self, queryset, name, value):
        return queryset.filter(hazard_type__in=value)

    def filter_start_year(self, queryset, name, value):
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        return queryset.filter(year__lte=value)

    def filter_countries_iso3(self, queryset, name, value):
        return queryset.filter(iso3__in=value)

    @property
    def qs(self):
        qs = super().qs
        return qs.filter(new_displacement__gt=0)


class ConflictStatisticsFilter(ReleaseMetadataFilter):
    countries = StringListFilter(method="filter_countries")
    start_year = django_filters.NumberFilter(method="filter_start_year")
    end_year = django_filters.NumberFilter(method="filter_end_year")
    countries_iso3 = StringListFilter(method="filter_countries_iso3")

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
    hazard_types = IDListFilter(method="filter_hazard_types")
    countries = StringListFilter(method="filter_countries")
    start_year = django_filters.NumberFilter(method="filter_start_year")
    end_year = django_filters.NumberFilter(method="filter_end_year")
    countries_iso3 = StringListFilter(method="filter_countries_iso3")

    class Meta:
        model = Disaster
        fields = ()

    def filter_hazard_types(self, queryset, name, value):
        return queryset.filter(hazard_type__in=value)

    def filter_countries(self, queryset, name, value):
        return queryset.filter(country__in=value)

    def filter_start_year(self, queryset, name, value):
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        return queryset.filter(year__lte=value)

    def filter_countries_iso3(self, queryset, name, value):
        return queryset.filter(iso3__in=value)


class GiddStatusLogFilter(django_filters.FilterSet):
    status = StringListFilter(method="filter_by_status")

    class Meta:
        model = StatusLog
        fields = ()

    def filter_by_status(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(status__in=value)
            return qs.filter(status__in=[StatusLog.Status.get(item).value for item in value])
        return qs


class PublicFigureAnalysisFilter(ReleaseMetadataFilter):
    class Meta:
        model = PublicFigureAnalysis
        fields = {
            "iso3": ["exact"],
            "year": ["exact"],
        }


class DisplacementDataFilter(ReleaseMetadataFilter):
    start_year = django_filters.NumberFilter(method="filter_start_year")
    end_year = django_filters.NumberFilter(method="filter_end_year")
    countries_iso3 = StringListFilter(method="filter_countries_iso3")
    cause = django_filters.ChoiceFilter(
        method="filter_cause",
        choices=get_name_choices(CRISIS_TYPE_PUBLIC),
    )

    class Meta:
        model = DisplacementData
        fields = ()

    def filter_start_year(self, queryset, name, value):
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        return queryset.filter(year__lte=value)

    def filter_countries_iso3(self, queryset, name, value):
        return queryset.filter(iso3__in=value)

    def filter_cause(self, queryset, name, value):
        if value.lower() == Crisis.CRISIS_TYPE.CONFLICT.name.lower():
            return queryset.filter(Q(conflict_new_displacement__gt=0) | Q(conflict_total_displacement__gt=0))
        elif value.lower() == Crisis.CRISIS_TYPE.DISASTER.name.lower():
            return queryset.filter(Q(disaster_new_displacement__gt=0) | Q(disaster_total_displacement__gt=0))
        return queryset

    @property
    def qs(self):
        qs = super().qs
        if "cause" not in self.data:
            return qs.filter(
                Q(conflict_new_displacement__gt=0)
                | Q(conflict_total_displacement__gt=0)
                | Q(disaster_new_displacement__gt=0)
                | Q(disaster_total_displacement__gt=0)
            )
        return qs


# Gidd filtets to api type map
GIDD_TRACKING_FILTERS = {
    DisasterFilter: ExternalApiDump.ExternalApiType.GIDD_DISASTER_GRAPHQL,
    ConflictFilter: ExternalApiDump.ExternalApiType.GIDD_CONFLICT_GRAPHQL,
    DisplacementDataFilter: ExternalApiDump.ExternalApiType.GIDD_DISPLACEMENT_DATA_GRAPHQL,
    PublicFigureAnalysisFilter: ExternalApiDump.ExternalApiType.GIDD_PFA_GRAPHQL,
    DisasterStatisticsFilter: ExternalApiDump.ExternalApiType.GIDD_DISASTER_STAT_GRAPHQL,
    ConflictStatisticsFilter: ExternalApiDump.ExternalApiType.GIDD_CONFLICT_STAT_GRAPHQL,
}

GIDD_API_TYPE_MAP = {
    # WHY? https://github.com/eamigo86/graphene-django-extras/blob/master/graphene_django_extras/filters/filter.py#L29
    f"{prefix}{filter_class.__name__}": api_type
    for prefix in ["Graphene", ""]
    for filter_class, api_type in GIDD_TRACKING_FILTERS.items()
}
