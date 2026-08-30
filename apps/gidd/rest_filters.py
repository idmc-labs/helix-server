import django_filters
from django.db.models import Q
from rest_framework import serializers

from apps.crisis.models import Crisis

from .enums import CRISIS_TYPE_PUBLIC
from .filters import ReleaseMetadataFilter, ValidatedYearFilterSet, YearFilter, clean_release_environment, get_name_choices
from .models import (
    GiddDisplacement,
    GiddEventDisplacement,
    GiddFigure,
    IdpsSaddEstimate,
    PublicFigureAnalysis,
    ReleaseMetadata,
)


class RestConflictFilterSet(ReleaseMetadataFilter):
    start_year = YearFilter(field_name="start_year", method="filter_start_year")
    end_year = YearFilter(field_name="end_year", method="filter_end_year")

    class Meta:
        model = GiddDisplacement
        fields = {
            # No `id` filter: this list is an aggregate over GiddDisplacement rows and has no pk
            # of its own.
            "iso3": ["iexact"],
            # The conflict typology levels the GraphQL surface accepts. They scope the rows that
            # feed the sums, so a total here always matches the selection that produced it.
            "violence": ["in"],
            "violence_sub_type": ["in"],
        }

    def filter_start_year(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(year__lte=value)


class RestDisasterFilterSet(ReleaseMetadataFilter):
    event_name = django_filters.CharFilter(method="filter_event_name")
    start_year = YearFilter(
        field_name="start_year",
        method="filter_start_year",
        help_text="Filter by start date",
    )
    end_year = YearFilter(
        field_name="end_year",
        method="filter_end_year",
        help_text="Filter by end date",
    )

    class Meta:
        model = GiddEventDisplacement
        fields = {
            "event_name": ["icontains"],
            "iso3": ["in"],
            # All four hazard levels, as on the GraphQL surface: a client holding a category or a
            # sub type cannot express it by enumerating the types beneath or above it.
            "hazard_category": ["in"],
            "hazard_sub_category": ["in"],
            "hazard_type": ["in"],
            "hazard_sub_type": ["in"],
        }

    def filter_event_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(event_name__icontains=value)

    def filter_start_year(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(year__lte=value)

    @property
    def qs(self):
        qs = super().qs
        # Keep events that report displacement of either kind: new displacement
        # (flow) or IDP stock.
        return qs.filter(Q(new_displacement__gt=0) | Q(total_displacement__gt=0))


class RestDisplacementDataFilterSet(ReleaseMetadataFilter):
    cause = django_filters.ChoiceFilter(
        method="filter_cause",
        choices=get_name_choices(CRISIS_TYPE_PUBLIC),
    )
    start_year = YearFilter(
        field_name="start_year",
        method="filter_start_year",
        help_text="Filter by start date",
    )
    end_year = YearFilter(
        field_name="end_year",
        method="filter_end_year",
        help_text="Filter by end date",
    )

    class Meta:
        model = GiddDisplacement
        fields = {
            "iso3": ["in"],
            # This list publishes both causes, so it carries both typologies. Each scopes the rows
            # that feed the sums; rows of the other cause carry none of these columns and drop out
            # entirely, so pair a violence filter with `cause=conflict` and a hazard filter with
            # `cause=disaster`.
            "violence": ["in"],
            "violence_sub_type": ["in"],
            "hazard_category": ["in"],
            "hazard_sub_category": ["in"],
            "hazard_type": ["in"],
            "hazard_sub_type": ["in"],
        }

    def filter_start_year(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(year__lte=value)

    def filter_cause(self, queryset, name, value):
        if not value:
            return queryset
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


class IdpsSaddEstimateFilter(ReleaseMetadataFilter):
    cause = django_filters.ChoiceFilter(
        method="filter_cause",
        choices=get_name_choices(CRISIS_TYPE_PUBLIC),
    )
    start_year = YearFilter(field_name="start_year", method="filter_start_year")
    end_year = YearFilter(field_name="end_year", method="filter_end_year")

    class Meta:
        model = IdpsSaddEstimate
        fields = {
            "iso3": ["in"],
        }

    def filter_start_year(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(year__lte=value)

    def filter_cause(self, queryset, name, value):
        if not value:
            return queryset
        # NOTE: this filter is used inside displacement export
        if value.lower() == Crisis.CRISIS_TYPE.CONFLICT.name.lower():
            return queryset.filter(
                cause=Crisis.CRISIS_TYPE.CONFLICT.value,
            )
        elif value.lower() == Crisis.CRISIS_TYPE.DISASTER.name.lower():
            return queryset.filter(
                cause=Crisis.CRISIS_TYPE.DISASTER.value,
            )
        return queryset


class PublicFigureAnalysisFilterSet(ReleaseMetadataFilter):
    cause = django_filters.ChoiceFilter(
        method="filter_cause",
        choices=get_name_choices(CRISIS_TYPE_PUBLIC),
    )
    start_year = YearFilter(
        field_name="start_year",
        method="filter_start_year",
        help_text="Filter by start date",
    )
    end_year = YearFilter(
        field_name="end_year",
        method="filter_end_year",
        help_text="Filter by end date",
    )

    class Meta:
        model = PublicFigureAnalysis
        fields = {
            "iso3": ["in"],
        }

    def filter_start_year(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(year__lte=value)

    def filter_cause(self, queryset, name, value):
        if not value:
            return queryset
        # NOTE: this filter is used inside displacement export
        if value.lower() == Crisis.CRISIS_TYPE.CONFLICT.name.lower():
            return queryset.filter(
                figure_cause=Crisis.CRISIS_TYPE.CONFLICT.value,
            )

        elif value.lower() == Crisis.CRISIS_TYPE.DISASTER.name.lower():
            return queryset.filter(
                figure_cause=Crisis.CRISIS_TYPE.DISASTER.value,
            )
        return queryset


class DisaggregationFilterSet(ValidatedYearFilterSet, django_filters.FilterSet):
    cause = django_filters.ChoiceFilter(
        method="filter_cause",
        choices=get_name_choices(CRISIS_TYPE_PUBLIC),
    )
    start_year = YearFilter(
        field_name="start_year",
        method="filter_start_year",
        help_text="Filter by start date",
    )
    end_year = YearFilter(
        field_name="end_year",
        method="filter_end_year",
        help_text="Filter by end date",
    )
    release_environment = django_filters.ChoiceFilter(
        method="no_op",
        choices=get_name_choices(ReleaseMetadata.ReleaseEnvironment),
    )

    class Meta:
        model = GiddFigure
        fields = {
            "iso3": ["in"],
            # The same six typology levels the GraphQL surface accepts; `GiddFigure` names the
            # hazard columns `disaster_*`, so the parameters here do too.
            "disaster_category": ["in"],
            "disaster_sub_category": ["in"],
            "disaster_type": ["in"],
            "disaster_sub_type": ["in"],
            "violence": ["in"],
            "violence_sub_type": ["in"],
        }

    def filter_start_year(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(year__lte=value)

    def filter_cause(self, queryset, name, value):
        if not value:
            return queryset
        if value.lower() == Crisis.CRISIS_TYPE.CONFLICT.name.lower():
            return queryset.filter(
                cause=Crisis.CRISIS_TYPE.CONFLICT.value,
            )

        elif value.lower() == Crisis.CRISIS_TYPE.DISASTER.name.lower():
            return queryset.filter(
                cause=Crisis.CRISIS_TYPE.DISASTER.value,
            )
        return queryset

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
        # Validated here rather than by the declared `ChoiceFilter`, which never runs: this
        # property reads `self.data` directly and so bypasses form cleaning.
        release_environment_name = clean_release_environment(self.data.get("release_environment"))
        qs = self.filter_release_environment(qs, release_environment_name)
        return qs


class DisaggregationPublicFigureAnalysisFilterSet(ValidatedYearFilterSet, django_filters.FilterSet):
    cause = django_filters.ChoiceFilter(
        method="filter_figure_cause",
        choices=get_name_choices(CRISIS_TYPE_PUBLIC),
    )
    start_year = YearFilter(
        field_name="start_year",
        method="filter_start_year",
        help_text="Filter by start date",
    )
    end_year = YearFilter(
        field_name="end_year",
        method="filter_end_year",
        help_text="Filter by end date",
    )
    release_environment = django_filters.ChoiceFilter(
        method="no_op",
        choices=get_name_choices(ReleaseMetadata.ReleaseEnvironment),
    )

    class Meta:
        model = PublicFigureAnalysis
        fields = {
            "iso3": ["in"],
        }

    def filter_figure_cause(self, qs, name, value):
        if not value:
            return qs
        # NOTE: this filter is used inside disaggregation export
        if value.lower() == Crisis.CRISIS_TYPE.CONFLICT.name.lower():
            return qs.filter(
                figure_cause=Crisis.CRISIS_TYPE.CONFLICT.value,
            )
        elif value.lower() == Crisis.CRISIS_TYPE.DISASTER.name.lower():
            return qs.filter(
                figure_cause=Crisis.CRISIS_TYPE.DISASTER.value,
            )
        return qs

    def filter_start_year(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(year__gte=value)

    def filter_end_year(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(year__lte=value)

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
        # Validated here rather than by the declared `ChoiceFilter`, which never runs: this
        # property reads `self.data` directly and so bypasses form cleaning.
        release_environment_name = clean_release_environment(self.data.get("release_environment"))
        qs = self.filter_release_environment(qs, release_environment_name)
        return qs


# The typology parameters a workbook's first sheet accepts and its companion sheets cannot.
# `PublicFigureAnalysis` and `IdpsSaddEstimate` carry no typology columns, so these are the
# requests that must reach them as country-years instead. Listed rather than derived, so a reader
# sees what triggers the narrowing without running the code;
# `test_the_narrowing_trigger_list_covers_every_unshared_filter` fails if a first sheet gains a
# filter that is not added here.
COMPANION_SHEET_NARROWING_FILTERS = (
    "violence__in",
    "violence_sub_type__in",
    "hazard_category__in",
    "hazard_sub_category__in",
    "hazard_type__in",
    "hazard_sub_type__in",
    "disaster_category__in",
    "disaster_sub_category__in",
    "disaster_type__in",
    "disaster_sub_type__in",
)


def companion_sheet_narrowing_requested(query_params) -> bool:
    """Whether the request carries a typology filter the companion sheets cannot express.

    `PublicFigureAnalysis` and `IdpsSaddEstimate` have no typology columns, so django-filter drops
    such a filter without a word -- publishing a workbook whose first sheet is narrowed beside
    sheets covering the whole release. The caller answers that by scoping to the country-years the
    first sheet kept. Nothing to do when no such filter was sent, and an unfiltered export is the
    slowest request these endpoints serve.
    """
    return any(any(value for value in query_params.getlist(name)) for name in COMPANION_SHEET_NARROWING_FILTERS)
