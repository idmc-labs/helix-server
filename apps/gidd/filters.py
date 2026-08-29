import typing

import django_filters
from rest_framework import serializers

from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.crisis.models import Crisis
from apps.entry.enums import FigureCategoryTypeEnum
from apps.entry.models import ExternalApiDump
from utils.filters import IDListFilter, SimpleInputFilter, StringListFilter

from .models import (
    GiddDisplacement,
    GiddEventDisplacement,
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
        # `or`, not a `.get` default: the argument is nullable, so an explicit null reaches this
        # as None and `.get`'s default never applies. RELEASE is the documented fallback.
        release_environment_name = self.data.get("release_environment") or ReleaseMetadata.ReleaseEnvironment.RELEASE.name
        qs = self.filter_release_environment(qs, release_environment_name)
        return qs


class ConflictStatisticsFilter(ReleaseMetadataFilter):
    start_year = django_filters.NumberFilter(method="filter_start_year")
    end_year = django_filters.NumberFilter(method="filter_end_year")
    countries_iso3 = StringListFilter(method="filter_countries_iso3")
    violence_types = IDListFilter(method="filter_violence_types")
    violence_sub_types = IDListFilter(method="filter_violence_sub_types")

    class Meta:
        model = GiddDisplacement
        fields = ()

    def filter_start_year(self, queryset, name, value):
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        return queryset.filter(year__lte=value)

    def filter_countries_iso3(self, queryset, name, value):
        return queryset.filter(iso3__in=value)

    def filter_violence_types(self, queryset, name, value):
        return queryset.filter(violence__in=value)

    def filter_violence_sub_types(self, queryset, name, value):
        return queryset.filter(violence_sub_type__in=value)

    @property
    def qs(self):
        return super().qs.filter(cause=Crisis.CRISIS_TYPE.CONFLICT)


class DisasterStatisticsFilter(ReleaseMetadataFilter):
    hazard_categories = IDListFilter(method="filter_hazard_categories")
    hazard_sub_categories = IDListFilter(method="filter_hazard_sub_categories")
    hazard_types = IDListFilter(method="filter_hazard_types")
    hazard_sub_types = IDListFilter(method="filter_hazard_sub_types")
    start_year = django_filters.NumberFilter(method="filter_start_year")
    end_year = django_filters.NumberFilter(method="filter_end_year")
    countries_iso3 = StringListFilter(method="filter_countries_iso3")

    class Meta:
        model = GiddDisplacement
        fields = ()

    def filter_hazard_categories(self, queryset, name, value):
        return queryset.filter(hazard_category__in=value)

    def filter_hazard_sub_categories(self, queryset, name, value):
        return queryset.filter(hazard_sub_category__in=value)

    def filter_hazard_types(self, queryset, name, value):
        return queryset.filter(hazard_type__in=value)

    def filter_hazard_sub_types(self, queryset, name, value):
        return queryset.filter(hazard_sub_type__in=value)

    def filter_start_year(self, queryset, name, value):
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        return queryset.filter(year__lte=value)

    def filter_countries_iso3(self, queryset, name, value):
        return queryset.filter(iso3__in=value)

    @property
    def qs(self):
        return super().qs.filter(cause=Crisis.CRISIS_TYPE.DISASTER)


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
    # Both columns are EnumFields, i.e. integer columns: a raw name reaches the ORM as a string
    # and `int("CONFLICT")` raises. An enum input also rejects unknown members before the ORM.
    figure_cause = SimpleInputFilter(CrisisTypeGrapheneEnum, field_name="figure_cause")
    figure_category = SimpleInputFilter(FigureCategoryTypeEnum, field_name="figure_category")

    class Meta:
        model = PublicFigureAnalysis
        # `iso3` and `year` only. The list forms of both were also declared, which made two ways to
        # ask one question, and the year list arrived typed as `[ID!]` -- a year is not an id.
        # Unlike the filtersets that carry `countries_iso3` as their only country filter, this one
        # already had the scalar.
        fields = {
            "iso3": ["exact"],
            "year": ["exact"],
        }


class GiddEventDisplacementFilter(ReleaseMetadataFilter):
    # A ChoiceFilter is unsafe here: django-filter drops a field that fails form validation from
    # `cleaned_data`, so an unknown cause is silently ignored and every row comes back.
    cause = SimpleInputFilter(CrisisTypeGrapheneEnum, field_name="cause")
    countries_iso3 = StringListFilter(method="filter_countries_iso3")
    start_year = django_filters.NumberFilter(method="filter_start_year")
    end_year = django_filters.NumberFilter(method="filter_end_year")
    hazard_categories = IDListFilter(method="filter_hazard_categories")
    hazard_sub_categories = IDListFilter(method="filter_hazard_sub_categories")
    hazard_types = IDListFilter(method="filter_hazard_types")
    hazard_sub_types = IDListFilter(method="filter_hazard_sub_types")
    violence_types = IDListFilter(method="filter_violence_types")
    violence_sub_types = IDListFilter(method="filter_violence_sub_types")
    event_name = django_filters.CharFilter(method="filter_event_name")
    events = IDListFilter(method="filter_events")

    class Meta:
        model = GiddEventDisplacement
        fields = {}

    def filter_countries_iso3(self, queryset, name, value):
        return queryset.filter(iso3__in=value)

    def filter_start_year(self, queryset, name, value):
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        return queryset.filter(year__lte=value)

    def filter_hazard_categories(self, queryset, name, value):
        return queryset.filter(hazard_category__in=value)

    def filter_hazard_sub_categories(self, queryset, name, value):
        return queryset.filter(hazard_sub_category__in=value)

    def filter_hazard_types(self, queryset, name, value):
        return queryset.filter(hazard_type__in=value)

    def filter_hazard_sub_types(self, queryset, name, value):
        return queryset.filter(hazard_sub_type__in=value)

    def filter_violence_types(self, queryset, name, value):
        return queryset.filter(violence__in=value)

    def filter_violence_sub_types(self, queryset, name, value):
        return queryset.filter(violence_sub_type__in=value)

    def filter_event_name(self, queryset, name, value):
        return queryset.filter(event_name__icontains=value)

    def filter_events(self, queryset, name, value):
        return queryset.filter(event_raw_id__in=value)


class GiddCountryDisplacementFilter(ReleaseMetadataFilter):
    # Scoping to one cause drops the other cause's rows before aggregation, so the country-years
    # that only carry the excluded cause fall out of the row filter and out of `total_count` --
    # which hiding the columns client-side cannot do.
    # A ChoiceFilter is unsafe here: django-filter drops a field that fails form validation from
    # `cleaned_data`, so an unknown cause is silently ignored and every row comes back.
    cause = SimpleInputFilter(CrisisTypeGrapheneEnum, field_name="cause")
    countries_iso3 = StringListFilter(method="filter_countries_iso3")
    start_year = django_filters.NumberFilter(method="filter_start_year")
    end_year = django_filters.NumberFilter(method="filter_end_year")

    class Meta:
        model = GiddDisplacement
        fields = {}

    def filter_countries_iso3(self, queryset, name, value):
        return queryset.filter(iso3__in=value)

    def filter_start_year(self, queryset, name, value):
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        return queryset.filter(year__lte=value)


# Gidd filtets to api type map
GIDD_TRACKING_FILTERS = {
    PublicFigureAnalysisFilter: ExternalApiDump.ExternalApiType.GIDD_PFA_GRAPHQL,
    DisasterStatisticsFilter: ExternalApiDump.ExternalApiType.GIDD_DISASTER_STAT_GRAPHQL,
    ConflictStatisticsFilter: ExternalApiDump.ExternalApiType.GIDD_CONFLICT_STAT_GRAPHQL,
    GiddEventDisplacementFilter: ExternalApiDump.ExternalApiType.GIDD_NEW_EVENTS_GRAPHQL,
}

GIDD_API_TYPE_MAP = {
    # WHY? https://github.com/eamigo86/graphene-django-extras/blob/master/graphene_django_extras/filters/filter.py#L29
    f"{prefix}{filter_class.__name__}": api_type
    for prefix in ["Graphene", ""]
    for filter_class, api_type in GIDD_TRACKING_FILTERS.items()
}
