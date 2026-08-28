# types.py
import graphene
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Coalesce
from graphene.utils.str_converters import to_snake_case
from graphene_django.filter.utils import get_filtering_args_from_filterset

from apps.country.models import Country
from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.crisis.models import Crisis
from apps.entry.enums import FigureCategoryTypeEnum
from apps.entry.models import ExternalApiDump
from utils.common import round_and_remove_zero, track_gidd
from utils.db import tiebreak_fields
from utils.graphene.enums import EnumDescription
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.ordering import strip_direction
from utils.graphene.pagination import PageGraphqlPaginationWithoutCount, get_page_size
from utils.graphene.relation_loaders import RelationBatchedDjangoObjectType
from utils.graphene.types import CustomDjangoListObjectType

from .enums import GiddStatusLogEnum
from .filters import (
    ConflictStatisticsFilter,
    DisasterStatisticsFilter,
    GiddCountryDisplacementFilter,
    GiddEventDisplacementFilter,
    GiddStatusLogFilter,
    PublicFigureAnalysisFilter,
    ReleaseMetadataFilter,
)
from .models import (
    GiddDisplacement,
    GiddEventDisplacement,
    PublicFigureAnalysis,
    ReleaseMetadata,
    StatusLog,
)


def default_end_year(kwargs):
    """IDPs are a stock: without an explicit endYear the snapshot year must default
    to the (pre-)release year, so `no year filter` returns the same response as
    `startYear=<first year>, endYear=<release year>` instead of summing every
    yearly snapshot."""
    release_meta_data = ReleaseMetadata.objects.last()
    if release_meta_data is None:
        return None
    environment = kwargs.get("release_environment") or ReleaseMetadata.ReleaseEnvironment.RELEASE.name
    if environment.lower() == ReleaseMetadata.ReleaseEnvironment.PRE_RELEASE.name.lower():
        return release_meta_data.pre_release_year
    return release_meta_data.release_year


def resolve_stock_year(kwargs, requested_end_year):
    """The year an IDP stock is read from, refusing a request beyond the published release.

    Rows stop at the (pre-)release year, so a later `endYear` would otherwise return a full
    new-displacement figure beside a zero stock -- a wrong answer that reads like a real one.
    """
    release_year = default_end_year(kwargs)
    if requested_end_year and release_year and requested_end_year > release_year:
        raise ValueError(f"endYear cannot be greater than the release year: {release_year}")
    return requested_end_year or release_year


def displacement_year_range(start_year, end_year):
    """The year scoping new displacement and IDP stock share.

    Both figures select rows the same way wherever a result row is itself one year -- the lists and
    the per-year timeseries. They diverge only where an aggregate collapses years: a flow sums the
    range, a stock must read a single one.
    """
    filters = {}
    if start_year:
        filters["year__gte"] = start_year
    if end_year:
        filters["year__lte"] = end_year
    return filters


def new_displacement_filters(start_year, end_year):
    """Rows with new displacement across the requested year range.

    A flow, so it is summed across the range; the `> 0` drops the rows the statistics queries
    treat as absent.
    """
    return {"new_displacement__gt": 0, **displacement_year_range(start_year, end_year)}


def idp_stock_filter(stock_year):
    """Rows carrying the IDP stock for `stock_year`, as a `Q` so an aggregate can AND it with a cause.

    A stock is point-in-time: read from one year, never summed across years.
    """
    return models.Q(total_displacement__gt=0, year=stock_year)


def cause_typology_filters(kwargs):
    """The conflict and disaster filters the country queries scope their sums with.

    Consumes the typology arguments from `kwargs` so what remains is the filterset's own. Both
    causes are bounded in one call because a request may narrow the disaster side by hazard and the
    conflict side by violence at once, and the two queries would otherwise drift apart -- they are
    the same filter written twice.

    All four hazard levels are accepted, matching the statistics and event queries; a caller
    bounding by category should not have to enumerate its types.
    """
    conflict_filter = Q(cause=Crisis.CRISIS_TYPE.CONFLICT)
    for argument, column in (
        ("violence_types", "violence"),
        ("violence_sub_types", "violence_sub_type"),
    ):
        value = kwargs.pop(argument, None)
        if value:
            conflict_filter &= Q(**{f"{column}__in": value})

    disaster_filter = Q(cause=Crisis.CRISIS_TYPE.DISASTER)
    for argument, column in (
        ("hazard_categories", "hazard_category"),
        ("hazard_sub_categories", "hazard_sub_category"),
        ("hazard_types", "hazard_type"),
        ("hazard_sub_types", "hazard_sub_type"),
    ):
        value = kwargs.pop(argument, None)
        if value:
            disaster_filter &= Q(**{f"{column}__in": value})

    return conflict_filter, disaster_filter


class GiddDisasterCountryType(graphene.ObjectType):
    id = graphene.Int(required=True)
    iso3 = graphene.String(required=True)
    country_name = graphene.String(required=True)


class GiddTimeSeriesStatisticsByYearType(graphene.ObjectType):
    year = graphene.Int(required=True)
    total = graphene.Int()
    total_rounded = graphene.Int()


class GiddTimeSeriesStatisticsByCountryType(graphene.ObjectType):
    year = graphene.Int(required=True)
    total = graphene.Int()
    total_rounded = graphene.Int()
    country = graphene.Field(GiddDisasterCountryType, required=True)


class DisplacementByHazardType(graphene.ObjectType):
    id = graphene.ID(required=True)
    label = graphene.String(required=True)
    new_displacements = graphene.Int()
    new_displacements_rounded = graphene.Int()
    total_displacements = graphene.Int()
    total_displacements_rounded = graphene.Int()


class DisplacementByViolenceType(graphene.ObjectType):
    id = graphene.ID(required=True)
    label = graphene.String(required=True)
    new_displacements = graphene.Int()
    new_displacements_rounded = graphene.Int()
    total_displacements = graphene.Int()
    total_displacements_rounded = graphene.Int()


class GiddConflictStatisticsType(graphene.ObjectType):
    new_displacements = graphene.Int()
    new_displacements_rounded = graphene.Int()
    total_displacements = graphene.Int()
    total_displacements_rounded = graphene.Int()
    total_displacement_countries = graphene.Int()
    internal_displacement_countries = graphene.Int()
    displacements_by_violence_sub_type = graphene.List(graphene.NonNull(DisplacementByViolenceType))
    new_displacement_timeseries_by_year = graphene.List(graphene.NonNull(GiddTimeSeriesStatisticsByYearType))
    new_displacement_timeseries_by_country = graphene.List(graphene.NonNull(GiddTimeSeriesStatisticsByCountryType))
    total_displacement_timeseries_by_year = graphene.List(graphene.NonNull(GiddTimeSeriesStatisticsByYearType))
    total_displacement_timeseries_by_country = graphene.List(graphene.NonNull(GiddTimeSeriesStatisticsByCountryType))


class GiddDisasterStatisticsType(graphene.ObjectType):
    new_displacements = graphene.Int()
    new_displacements_rounded = graphene.Int()
    total_events = graphene.Int()
    displacements_by_hazard_type = graphene.List(graphene.NonNull(DisplacementByHazardType))

    total_displacement_countries = graphene.Int()
    internal_displacement_countries = graphene.Int()
    total_displacements = graphene.Int()
    total_displacements_rounded = graphene.Int()

    new_displacement_timeseries_by_year = graphene.List(graphene.NonNull(GiddTimeSeriesStatisticsByYearType))
    new_displacement_timeseries_by_country = graphene.List(graphene.NonNull(GiddTimeSeriesStatisticsByCountryType))
    total_displacement_timeseries_by_year = graphene.List(graphene.NonNull(GiddTimeSeriesStatisticsByYearType))
    total_displacement_timeseries_by_country = graphene.List(graphene.NonNull(GiddTimeSeriesStatisticsByCountryType))


class GiddCombinedStatisticsType(graphene.ObjectType):
    internal_displacements = graphene.Int()
    total_displacements = graphene.Int()
    internal_displacements_rounded = graphene.Int()
    total_displacements_rounded = graphene.Int()
    internal_displacement_countries = graphene.Int()
    total_displacement_countries = graphene.Int()


class GiddStatusLogType(RelationBatchedDjangoObjectType):
    class Meta:
        model = StatusLog
        # Pinned, not excluded, so a column added to StatusLog later does not join the payload on
        # its own. `triggered_by` is listed deliberately: the admin client renders it, and this
        # type is not whitelisted, so it never reaches an unauthenticated caller.
        fields = ("id", "triggered_at", "completed_at", "status", "triggered_by")

    status = graphene.Field(GiddStatusLogEnum)
    status_display = EnumDescription(source="get_status_display")


class GiddStatusLogListType(CustomDjangoListObjectType):
    class Meta:
        model = StatusLog
        filterset_class = GiddStatusLogFilter


class GiddPublicFigureAnalysisType(RelationBatchedDjangoObjectType):
    class Meta:
        model = PublicFigureAnalysis
        fields = (
            "id",
            "iso3",
            "year",
            "figures",
            "figures_rounded",
            "description",
        )

    figure_cause = graphene.Field(CrisisTypeGrapheneEnum)
    figure_cause_display = EnumDescription(source="get_figure_cause_display")
    figure_category = graphene.Field(FigureCategoryTypeEnum)
    figure_category_display = EnumDescription(source="get_figure_category_display")


class GiddPublicFigureAnalysisListType(CustomDjangoListObjectType):
    class Meta:
        model = PublicFigureAnalysis
        filterset_class = PublicFigureAnalysisFilter


class GiddEventDisplacementType(RelationBatchedDjangoObjectType):
    country_id = graphene.ID(required=True)
    event_id = graphene.ID()
    cause = graphene.Field(CrisisTypeGrapheneEnum)
    cause_display = EnumDescription(source="get_cause_display")
    violence_id = graphene.ID()
    violence_sub_type_id = graphene.ID()
    hazard_category_id = graphene.ID()
    hazard_sub_category_id = graphene.ID()
    hazard_type_id = graphene.ID()
    hazard_sub_type_id = graphene.ID()

    class Meta:
        model = GiddEventDisplacement
        fields = (
            "id",
            "event_name",
            "iso3",
            "country_name",
            "year",
            "start_date",
            "end_date",
            "event_codes",
            "violence_name",
            "violence_sub_type_name",
            "hazard_category_name",
            "hazard_sub_category_name",
            "hazard_type_name",
            "hazard_sub_type_name",
            "new_displacement",
            "new_displacement_rounded",
            "total_displacement",
            "total_displacement_rounded",
        )

    @staticmethod
    def resolve_event_id(root, info, **kwargs):
        return root.event_raw_id


class GiddEventDisplacementListType(CustomDjangoListObjectType):
    class Meta:
        model = GiddEventDisplacement
        filterset_class = GiddEventDisplacementFilter


class GiddReleaseMetadataType(RelationBatchedDjangoObjectType):
    class Meta:
        model = ReleaseMetadata
        # giddPublicReleaseMetaData is whitelisted and WhiteListMiddleware checks only the root
        # node, so anything this type reaches is readable unauthenticated -- `modified_by` would
        # expose UserType. Pinned rather than excluded so a new model column stays invisible.
        # TODO(frontend): read this for the maximum allowed year; no client consumes it yet.
        fields = (
            "id",
            "release_year",
            "pre_release_year",
        )


class GiddPublicCountryRegionType(graphene.ObjectType):
    id = graphene.ID(required=True)
    name = graphene.String(required=True)


class GiddPublicCountryGeographicalGroupType(graphene.ObjectType):
    id = graphene.ID(required=True)
    name = graphene.String(required=True)


class GiddPublicCountryType(graphene.ObjectType):
    id = graphene.ID(required=True)
    iso3 = graphene.String(required=True)
    idmc_short_name = graphene.String(required=True)
    region = graphene.Field(GiddPublicCountryRegionType)
    geographical_group = graphene.Field(GiddPublicCountryGeographicalGroupType)
    centroid = graphene.List(graphene.Float)


class GiddHazardType(graphene.ObjectType):
    id = graphene.ID(required=True)
    name = graphene.String(required=True)


class GiddHazardSubCategoryType(graphene.ObjectType):
    id = graphene.ID(required=True)
    name = graphene.String(required=True)


class GiddViolenceSubType(graphene.ObjectType):
    id = graphene.ID(required=True)
    name = graphene.String(required=True)


class GiddYearType(graphene.ObjectType):
    year = graphene.Int(required=True)


class GiddEventAffectedCountryType(graphene.ObjectType):
    iso3 = graphene.String(required=True)
    country_name = graphene.String(required=True)
    new_displacement = graphene.Int()
    new_displacement_rounded = graphene.Int()


class GiddEventType(graphene.ObjectType):
    event_name = graphene.String(required=True)
    new_displacement = graphene.Int()
    new_displacement_rounded = graphene.Int()
    start_date = graphene.Date(required=True)
    end_date = graphene.Date(required=True)
    event_codes = graphene.List(
        graphene.NonNull(graphene.String),
        required=True,
    )
    event_codes_type = graphene.List(
        graphene.NonNull(graphene.String),
        required=True,
    )
    affected_countries = graphene.List(
        GiddEventAffectedCountryType,
    )
    hazard_types = graphene.List(
        GiddHazardType,
    )


class GiddCountryDisplacementType(graphene.ObjectType):
    iso3 = graphene.String(required=True)
    country_name = graphene.String(required=True)
    country_id = graphene.ID(required=True)
    conflict_new_displacement = graphene.Int()
    conflict_new_displacement_rounded = graphene.Int()
    conflict_total_displacement = graphene.Int()
    conflict_total_displacement_rounded = graphene.Int()
    disaster_new_displacement = graphene.Int()
    disaster_new_displacement_rounded = graphene.Int()
    disaster_total_displacement = graphene.Int()
    disaster_total_displacement_rounded = graphene.Int()


class GiddCountryYearDisplacementType(graphene.ObjectType):
    iso3 = graphene.String(required=True)
    country_name = graphene.String(required=True)
    country_id = graphene.ID(required=True)
    year = graphene.Int(required=True)
    conflict_new_displacement = graphene.Int()
    conflict_new_displacement_rounded = graphene.Int()
    conflict_total_displacement = graphene.Int()
    conflict_total_displacement_rounded = graphene.Int()
    disaster_new_displacement = graphene.Int()
    disaster_new_displacement_rounded = graphene.Int()
    disaster_total_displacement = graphene.Int()
    disaster_total_displacement_rounded = graphene.Int()


GIDD_COUNTRY_YEAR_DEFAULT_PAGE_SIZE = 50
# `get_page_size` rejects an over-large value rather than quietly serving fewer rows.
GIDD_COUNTRY_YEAR_MAX_PAGE_SIZE = settings.GRAPHENE_DJANGO_EXTRAS["MAX_PAGE_SIZE"]

# Kept in step with GiddDisplacement.ORDERING_ALLOWLIST, which the allowlist registry test
# enumerates. Every key is a column this query also returns, so a client sorts by what it reads.
GIDD_COUNTRY_YEAR_SORTABLE = frozenset(
    {
        "conflict_new_displacement",
        "conflict_total_displacement",
        "country_name",
        "disaster_new_displacement",
        "disaster_total_displacement",
        "iso3",
        "year",
    }
)


class GiddCountryYearDisplacementListType(graphene.ObjectType):
    results = graphene.List(graphene.NonNull(GiddCountryYearDisplacementType), required=True)
    total_count = graphene.Int(required=True)
    page = graphene.Int(required=True)
    page_size = graphene.Int(required=True)


class Query(graphene.ObjectType):
    gidd_public_conflict_statistics = graphene.Field(
        GiddConflictStatisticsType,
        **get_filtering_args_from_filterset(ConflictStatisticsFilter, GiddConflictStatisticsType),
        required=True,
        client_id=graphene.String(required=True),
    )
    gidd_public_disaster_statistics = graphene.Field(
        GiddDisasterStatisticsType,
        **get_filtering_args_from_filterset(DisasterStatisticsFilter, GiddDisasterStatisticsType),
        required=True,
        client_id=graphene.String(required=True),
    )
    gidd_logs = DjangoPaginatedListObjectField(
        GiddStatusLogListType,
        pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize"),
    )
    gidd_release_meta_data = graphene.Field(
        GiddReleaseMetadataType,
    )
    gidd_public_countries = graphene.List(
        graphene.NonNull(GiddPublicCountryType),
        client_id=graphene.String(required=True),
    )
    gidd_public_hazard_types = graphene.List(
        GiddHazardType,
        client_id=graphene.String(required=True),
    )
    gidd_public_violence_sub_types = graphene.List(
        GiddViolenceSubType,
        client_id=graphene.String(required=True),
    )
    gidd_public_figure_analysis_list = DjangoPaginatedListObjectField(
        GiddPublicFigureAnalysisListType,
        pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize"),
        client_id=graphene.String(required=True),
    )
    gidd_public_year = graphene.Field(
        graphene.NonNull(GiddYearType),
        release_environment=graphene.String(required=True),
        client_id=graphene.String(required=True),
    )
    gidd_public_event = graphene.Field(
        GiddEventType,
        event_id=graphene.ID(required=True),
        **get_filtering_args_from_filterset(ReleaseMetadataFilter, GiddEventType),
        client_id=graphene.String(required=True),
    )
    gidd_public_combined_statistics = graphene.Field(
        GiddCombinedStatisticsType,
        **get_filtering_args_from_filterset(DisasterStatisticsFilter, GiddCombinedStatisticsType),
        required=True,
        client_id=graphene.String(required=True),
    )
    gidd_public_displacement_events = DjangoPaginatedListObjectField(
        GiddEventDisplacementListType,
        pagination=PageGraphqlPaginationWithoutCount(page_size_query_param="pageSize", page_size=50),
        client_id=graphene.String(required=True),
    )
    gidd_public_country_displacements = graphene.Field(
        graphene.List(graphene.NonNull(GiddCountryDisplacementType)),
        **get_filtering_args_from_filterset(GiddCountryDisplacementFilter, GiddCountryDisplacementType),
        hazard_categories=graphene.List(graphene.NonNull(graphene.ID)),
        hazard_sub_categories=graphene.List(graphene.NonNull(graphene.ID)),
        hazard_types=graphene.List(graphene.NonNull(graphene.ID)),
        hazard_sub_types=graphene.List(graphene.NonNull(graphene.ID)),
        violence_types=graphene.List(graphene.NonNull(graphene.ID)),
        violence_sub_types=graphene.List(graphene.NonNull(graphene.ID)),
        client_id=graphene.String(required=True),
    )
    gidd_public_country_year_displacements = graphene.Field(
        GiddCountryYearDisplacementListType,
        **get_filtering_args_from_filterset(GiddCountryDisplacementFilter, GiddCountryYearDisplacementType),
        hazard_categories=graphene.List(graphene.NonNull(graphene.ID)),
        hazard_sub_categories=graphene.List(graphene.NonNull(graphene.ID)),
        hazard_types=graphene.List(graphene.NonNull(graphene.ID)),
        hazard_sub_types=graphene.List(graphene.NonNull(graphene.ID)),
        violence_types=graphene.List(graphene.NonNull(graphene.ID)),
        violence_sub_types=graphene.List(graphene.NonNull(graphene.ID)),
        page=graphene.Int(description="1-indexed page number (default 1)."),
        page_size=graphene.Int(
            description=(
                f"Rows per page (default {GIDD_COUNTRY_YEAR_DEFAULT_PAGE_SIZE}, max {GIDD_COUNTRY_YEAR_MAX_PAGE_SIZE})."
            )
        ),
        ordering=graphene.String(
            description=(
                "Comma-separated sort keys, prefix with '-' for descending "
                "(e.g. '-conflictTotalDisplacement,iso3'). Allowed: iso3, countryName, year, "
                "conflictNewDisplacement, conflictTotalDisplacement, disasterNewDisplacement, "
                "disasterTotalDisplacement. Defaults to iso3, year."
            ),
        ),
        client_id=graphene.String(required=True),
    )

    @staticmethod
    def resolve_gidd_release_meta_data(parent, info, **kwargs):
        return ReleaseMetadata.objects.last()

    @staticmethod
    def resolve_gidd_public_countries(parent, info, **kwargs):
        # Track
        client_id = kwargs.pop("client_id")
        track_gidd(client_id, ExternalApiDump.ExternalApiType.GIDD_PUBLIC_COUNTRIES_GRAPHQL)

        return [
            GiddPublicCountryType(
                id=country["id"],
                iso3=country["iso3"],
                idmc_short_name=country["idmc_short_name"],
                centroid=country["centroid"],
                region=GiddPublicCountryRegionType(
                    id=country["region__id"],
                    name=country["region__name"],
                ),
                geographical_group=(
                    GiddPublicCountryGeographicalGroupType(
                        id=country["geographical_group__id"],
                        name=country["geographical_group__name"],
                    )
                    if country["geographical_group__id"] is not None
                    else None
                ),
            )
            for country in Country.objects.values(
                "id",
                "idmc_short_name",
                "iso3",
                "centroid",
                "region__id",
                "region__name",
                "geographical_group__id",
                "geographical_group__name",
            )
        ]

    @staticmethod
    def resolve_gidd_public_conflict_statistics(parent, info, **kwargs):
        # Track
        client_id = kwargs.pop("client_id")
        track_gidd(client_id, ExternalApiDump.ExternalApiType.GIDD_CONFLICT_STAT_GRAPHQL)

        conflict_qs = ConflictStatisticsFilter(data=kwargs).qs
        start_year = kwargs.pop("start_year", None)
        end_year = resolve_stock_year(kwargs, kwargs.pop("end_year", None))
        filters = new_displacement_filters(start_year, end_year)

        conflict_stock_year = end_year
        conflict_total_displacement_qs = conflict_qs.filter(idp_stock_filter(conflict_stock_year))
        conflict_new_displacement_qs = ConflictStatisticsFilter(data=kwargs).qs.filter(**filters)

        new_displacement_timeseries_by_year_qs = (
            conflict_qs.filter(new_displacement__gt=0)
            .values("year")
            .annotate(total=Coalesce(models.Sum("new_displacement", output_field=models.IntegerField()), 0))
            .order_by("year")
            .values("year", "total")
        )

        new_displacement_timeseries_by_country_qs = (
            conflict_qs.filter(new_displacement__gt=0)
            .values("year")
            .annotate(total=Coalesce(models.Sum("new_displacement", output_field=models.IntegerField()), 0))
            .order_by("year")
            .values("year", "total", "country_id", "country_name", "iso3")
        )

        total_displacement_timeseries_by_year_qs = (
            conflict_qs.filter(total_displacement__gt=0)
            .values("year")
            .annotate(total=Coalesce(models.Sum("total_displacement", output_field=models.IntegerField()), 0))
            .order_by("year")
            .values("year", "total")
        )

        total_displacement_timeseries_by_country_qs = (
            conflict_qs.filter(total_displacement__gt=0)
            .values("year")
            .annotate(total=Coalesce(models.Sum("total_displacement", output_field=models.IntegerField()), 0))
            .order_by("year")
            .values("year", "total", "country_id", "country_name", "iso3")
        )

        # IDP stock is point-in-time, so the per-category total stays inside the one year.
        violence_categories_qs = (
            conflict_qs.values("violence_sub_type", "violence_sub_type__id")
            .annotate(
                total=Coalesce(models.Sum("new_displacement", output_field=models.IntegerField()), 0),
                total_idp=Coalesce(
                    models.Sum(
                        "total_displacement",
                        filter=idp_stock_filter(conflict_stock_year),
                        output_field=models.IntegerField(),
                    ),
                    0,
                ),
                label=models.Case(
                    models.When(violence_sub_type=None, then=models.Value("Not labeled")),
                    default=models.F("violence_sub_type_name"),
                    output_field=models.CharField(),
                ),
            )
            .filter(total__gt=0)
        )

        return GiddConflictStatisticsType(
            new_displacements_rounded=round_and_remove_zero(
                conflict_new_displacement_qs.aggregate(
                    total=Coalesce(models.Sum("new_displacement", output_field=models.IntegerField()), 0)
                )["total"]
            ),
            new_displacements=conflict_new_displacement_qs.aggregate(
                total=Coalesce(models.Sum("new_displacement", output_field=models.IntegerField()), 0)
            )["total"],
            total_displacements_rounded=round_and_remove_zero(
                conflict_total_displacement_qs.aggregate(
                    total=Coalesce(models.Sum("total_displacement", output_field=models.IntegerField()), 0)
                )["total"]
            ),
            total_displacements=conflict_total_displacement_qs.aggregate(
                total=Coalesce(models.Sum("total_displacement", output_field=models.IntegerField()), 0)
            )["total"],
            total_displacement_countries=conflict_total_displacement_qs.distinct("iso3").count(),
            internal_displacement_countries=conflict_new_displacement_qs.distinct("iso3").count(),
            displacements_by_violence_sub_type=[
                DisplacementByViolenceType(
                    id=item["violence_sub_type__id"],
                    label=item["label"],
                    new_displacements=item["total"],
                    new_displacements_rounded=round_and_remove_zero(item["total"]),
                    total_displacements=item["total_idp"],
                    total_displacements_rounded=round_and_remove_zero(item["total_idp"]),
                )
                for item in violence_categories_qs
            ],
            new_displacement_timeseries_by_year=[
                GiddTimeSeriesStatisticsByYearType(
                    year=item["year"],
                    total=item["total"],
                    total_rounded=round_and_remove_zero(item["total"]),
                )
                for item in new_displacement_timeseries_by_year_qs
            ],
            new_displacement_timeseries_by_country=[
                GiddTimeSeriesStatisticsByCountryType(
                    year=item["year"],
                    total_rounded=round_and_remove_zero(item["total"]),
                    total=item["total"],
                    country=GiddDisasterCountryType(
                        id=item["country_id"], iso3=item["iso3"], country_name=item["country_name"]
                    ),
                )
                for item in new_displacement_timeseries_by_country_qs
            ],
            total_displacement_timeseries_by_year=[
                GiddTimeSeriesStatisticsByYearType(
                    year=item["year"],
                    total=item["total"],
                    total_rounded=round_and_remove_zero(item["total"]),
                )
                for item in total_displacement_timeseries_by_year_qs
            ],
            total_displacement_timeseries_by_country=[
                GiddTimeSeriesStatisticsByCountryType(
                    year=item["year"],
                    total_rounded=round_and_remove_zero(item["total"]),
                    total=item["total"],
                    country=GiddDisasterCountryType(
                        id=item["country_id"], iso3=item["iso3"], country_name=item["country_name"]
                    ),
                )
                for item in total_displacement_timeseries_by_country_qs
            ],
        )

    @staticmethod
    def resolve_gidd_public_disaster_statistics(parent, info, **kwargs):
        # Track
        client_id = kwargs.pop("client_id")
        track_gidd(client_id, ExternalApiDump.ExternalApiType.GIDD_DISASTER_STAT_GRAPHQL)

        disaster_qs = DisasterStatisticsFilter(data=kwargs).qs
        # Copied before the pops below, which mutate kwargs.
        event_filter_data = dict(kwargs)
        start_year = kwargs.pop("start_year", None)
        end_year = resolve_stock_year(kwargs, kwargs.pop("end_year", None))
        filters = new_displacement_filters(start_year, end_year)

        disaster_stock_year = end_year
        disaster_total_displacement_qs = disaster_qs.filter(idp_stock_filter(disaster_stock_year))
        disaster_new_displacement_qs = DisasterStatisticsFilter(data=kwargs).qs.filter(**filters)

        new_displacement_timeseries_by_year_qs = (
            disaster_qs.filter(new_displacement__gt=0)
            .values("year")
            .annotate(total=Coalesce(models.Sum("new_displacement", output_field=models.IntegerField()), 0))
            .order_by("year")
            .values("year", "total")
        )

        new_displacement_timeseries_by_country_qs = (
            disaster_qs.filter(new_displacement__gt=0)
            .values("year")
            .annotate(total=Coalesce(models.Sum("new_displacement", output_field=models.IntegerField()), 0))
            .order_by("year")
            .values("year", "total", "country_id", "country_name", "iso3")
        )

        total_displacement_timeseries_by_year_qs = (
            disaster_qs.filter(total_displacement__gt=0)
            .values("year")
            .annotate(total=Coalesce(models.Sum("total_displacement", output_field=models.IntegerField()), 0))
            .order_by("year")
            .values("year", "total")
        )

        total_displacement_timeseries_by_country_qs = (
            disaster_qs.filter(total_displacement__gt=0)
            .values("year")
            .annotate(total=Coalesce(models.Sum("total_displacement", output_field=models.IntegerField()), 0))
            .order_by("year")
            .values("year", "total", "country_id", "country_name", "iso3")
        )

        # IDP stock is point-in-time, so the per-category total stays inside the one year.
        categories_qs = (
            disaster_qs.values("hazard_type", "hazard_type__id")
            .annotate(
                total=Coalesce(models.Sum("new_displacement", output_field=models.IntegerField()), 0),
                total_idp=Coalesce(
                    models.Sum(
                        "total_displacement",
                        filter=idp_stock_filter(disaster_stock_year),
                        output_field=models.IntegerField(),
                    ),
                    0,
                ),
                label=models.Case(
                    models.When(hazard_type=None, then=models.Value("Not labeled")),
                    default=models.F("hazard_type_name"),
                    output_field=models.CharField(),
                ),
            )
            .filter(total__gt=0)
        )

        return GiddDisasterStatisticsType(
            new_displacements_rounded=round_and_remove_zero(
                disaster_new_displacement_qs.aggregate(
                    total=Coalesce(models.Sum("new_displacement", output_field=models.IntegerField()), 0)
                )["total"]
            ),
            new_displacements=disaster_new_displacement_qs.aggregate(
                total=Coalesce(models.Sum("new_displacement", output_field=models.IntegerField()), 0)
            )["total"],
            total_displacements_rounded=round_and_remove_zero(
                disaster_total_displacement_qs.aggregate(
                    total=Coalesce(models.Sum("total_displacement", output_field=models.IntegerField()), 0)
                )["total"]
            ),
            total_displacements=disaster_total_displacement_qs.aggregate(
                total=Coalesce(models.Sum("total_displacement", output_field=models.IntegerField()), 0)
            )["total"],
            total_events=GiddEventDisplacementFilter(data=event_filter_data)
            .qs.filter(
                cause=Crisis.CRISIS_TYPE.DISASTER,
                **filters,
            )
            .filter(models.Q(new_displacement__gt=0) | models.Q(total_displacement__gt=0))
            .count(),
            total_displacement_countries=disaster_total_displacement_qs.distinct("iso3").count(),
            internal_displacement_countries=disaster_new_displacement_qs.distinct("iso3").count(),
            new_displacement_timeseries_by_year=[
                GiddTimeSeriesStatisticsByYearType(
                    year=item["year"],
                    total_rounded=round_and_remove_zero(item["total"]),
                    total=item["total"],
                )
                for item in new_displacement_timeseries_by_year_qs
            ],
            new_displacement_timeseries_by_country=[
                GiddTimeSeriesStatisticsByCountryType(
                    year=item["year"],
                    total_rounded=round_and_remove_zero(item["total"]),
                    total=item["total"],
                    country=GiddDisasterCountryType(
                        id=item["country_id"], iso3=item["iso3"], country_name=item["country_name"]
                    ),
                )
                for item in new_displacement_timeseries_by_country_qs
            ],
            total_displacement_timeseries_by_year=[
                GiddTimeSeriesStatisticsByYearType(
                    year=item["year"],
                    total_rounded=round_and_remove_zero(item["total"]),
                    total=item["total"],
                )
                for item in total_displacement_timeseries_by_year_qs
            ],
            total_displacement_timeseries_by_country=[
                GiddTimeSeriesStatisticsByCountryType(
                    year=item["year"],
                    total=item["total"],
                    total_rounded=round_and_remove_zero(item["total"]),
                    country=GiddDisasterCountryType(
                        id=item["country_id"], iso3=item["iso3"], country_name=item["country_name"]
                    ),
                )
                for item in total_displacement_timeseries_by_country_qs
            ],
            displacements_by_hazard_type=[
                DisplacementByHazardType(
                    id=item["hazard_type__id"],
                    label=item["label"],
                    new_displacements=item["total"],
                    new_displacements_rounded=round_and_remove_zero(item["total"]),
                    total_displacements=item["total_idp"],
                    total_displacements_rounded=round_and_remove_zero(item["total_idp"]),
                )
                for item in categories_qs
            ],
        )

    @staticmethod
    def resolve_gidd_public_hazard_types(parent, info, **kwargs):
        # Track
        client_id = kwargs.pop("client_id")
        track_gidd(client_id, ExternalApiDump.ExternalApiType.GIDD_HAZARD_TYPES_GRAPHQL)

        return [
            GiddHazardType(
                id=hazard["hazard_type__id"],
                name=hazard["hazard_type__name"],
            )
            for hazard in GiddDisplacement.objects.filter(
                cause=Crisis.CRISIS_TYPE.DISASTER,
                hazard_type__isnull=False,
            )
            .values("hazard_type__id", "hazard_type__name")
            .distinct("hazard_type__id", "hazard_type__name")
        ]

    @staticmethod
    def resolve_gidd_public_violence_sub_types(parent, info, **kwargs):
        client_id = kwargs.pop("client_id")
        track_gidd(client_id, ExternalApiDump.ExternalApiType.GIDD_VIOLENCE_SUB_TYPES_GRAPHQL)

        return [
            GiddViolenceSubType(
                id=row["violence_sub_type__id"],
                name=row["violence_sub_type_name"],
            )
            for row in GiddDisplacement.objects.filter(
                cause=Crisis.CRISIS_TYPE.CONFLICT,
                violence_sub_type__isnull=False,
            )
            .values("violence_sub_type__id", "violence_sub_type_name")
            .distinct("violence_sub_type__id", "violence_sub_type_name")
        ]

    @staticmethod
    def resolve_gidd_public_year(parent, info, **kwargs):
        # Track
        client_id = kwargs.pop("client_id")
        track_gidd(client_id, ExternalApiDump.ExternalApiType.GIDD_YEAR_GRAPHQL)

        gidd_meta_data = ReleaseMetadata.objects.last()
        if kwargs["release_environment"].lower() == ReleaseMetadata.ReleaseEnvironment.PRE_RELEASE.name.lower():
            return GiddYearType(year=gidd_meta_data.pre_release_year)
        if kwargs["release_environment"].lower() == ReleaseMetadata.ReleaseEnvironment.RELEASE.name.lower():
            return GiddYearType(year=gidd_meta_data.release_year)

    @staticmethod
    def resolve_gidd_public_event(parent, info, **kwargs):
        # Track
        client_id = kwargs.pop("client_id")
        track_gidd(client_id, ExternalApiDump.ExternalApiType.GIDD_EVENT_GRAPHQL)

        event_id = kwargs["event_id"]
        # Not cause-scoped: an event is resolved across conflict and disaster rows alike, and
        # carries one row per country it touched.
        event_qs = GiddEventDisplacementFilter(data=kwargs).qs.filter(event_raw_id=event_id)

        if not event_qs.exists():
            return None

        base = event_qs.values(
            "event_name",
            "start_date",
            "end_date",
            "all_country_event_codes",
            "all_country_event_codes_type",
        ).first()
        total_new_displacement = event_qs.aggregate(total=models.Sum("new_displacement"))["total"]

        # The all-country columns, not the row-scoped `event_codes`: a country that registered a
        # code but produced no figures has no row here, so aggregating rows would drop its code.
        event_codes = (base or {}).get("all_country_event_codes") or []
        event_codes_type = (base or {}).get("all_country_event_codes_type") or []

        affected_countries_qs = (
            event_qs.values(
                "country_name",
                "iso3",
            )
            .order_by()
            .annotate(
                total_new_displacement=models.Sum("new_displacement"),
            )
        )

        hazard_types_qs = (
            event_qs.filter(hazard_type__isnull=False)
            # hazard_type_name is denormalised onto the row, so the published name is the one the
            # release captured rather than the live table's current value.
            .values("hazard_type_id", "hazard_type_name")
            .distinct("hazard_type_id", "hazard_type_name")
        )
        return GiddEventType(
            event_name=base.get("event_name"),
            new_displacement_rounded=round_and_remove_zero(total_new_displacement),
            new_displacement=total_new_displacement,
            start_date=base.get("start_date"),
            end_date=base.get("end_date"),
            event_codes=event_codes,
            event_codes_type=event_codes_type,
            affected_countries=[
                GiddEventAffectedCountryType(
                    iso3=country_data["iso3"],
                    country_name=country_data["country_name"],
                    new_displacement_rounded=round_and_remove_zero(country_data["total_new_displacement"]),
                    new_displacement=country_data["total_new_displacement"],
                )
                for country_data in affected_countries_qs
            ],
            hazard_types=[
                GiddHazardType(
                    id=hazard_type["hazard_type_id"],
                    name=hazard_type["hazard_type_name"],
                )
                for hazard_type in hazard_types_qs
            ],
        )

    @staticmethod
    def resolve_gidd_public_combined_statistics(parent, info, **kwargs):
        # Track
        client_id = kwargs.pop("client_id")
        track_gidd(client_id, ExternalApiDump.ExternalApiType.GIDD_COMBINED_STAT_GRAPHQL)

        start_year = kwargs.pop("start_year", None)
        end_year = resolve_stock_year(kwargs, kwargs.pop("end_year", None))

        filters = new_displacement_filters(start_year, end_year)

        disaster_base = DisasterStatisticsFilter(data=kwargs).qs
        disaster_total_displacement_qs = disaster_base.filter(idp_stock_filter(end_year))
        disaster_internal_displacement_qs = DisasterStatisticsFilter(data=kwargs).qs.filter(**filters)

        disaster_total_displacement_stats = disaster_total_displacement_qs.aggregate(
            models.Sum("total_displacement"),
        )
        disaster_internal_displacement_stats = disaster_internal_displacement_qs.aggregate(
            models.Sum("new_displacement"),
        )

        disaster_total_displacement_countries = (
            disaster_total_displacement_qs.order_by().values_list("iso3", flat=True).distinct()
        )
        disaster_internal_displacement_countries = (
            disaster_internal_displacement_qs.order_by().values_list("iso3", flat=True).distinct()
        )

        # Hazard filters scope the disaster side only, so the combined figure stays every conflict
        # row plus the matching disaster rows -- a true total for the scope asked about rather than
        # a disaster-only figure under a combined name. ConflictStatisticsFilter would ignore these
        # keys anyway; dropping them keeps both call sites' inputs explicit.
        conflict_kwargs = {
            key: value
            for key, value in kwargs.items()
            if key not in ("hazard_types", "hazard_sub_types", "hazard_categories", "hazard_sub_categories")
        }

        conflict_base = ConflictStatisticsFilter(data=conflict_kwargs).qs
        conflict_total_displacement_qs = conflict_base.filter(idp_stock_filter(end_year))
        conflict_internal_displacement_qs = ConflictStatisticsFilter(data=conflict_kwargs).qs.filter(**filters)

        conflict_total_displacement_stats = conflict_total_displacement_qs.aggregate(
            models.Sum("total_displacement"),
        )
        conflict_internal_displacement_stats = conflict_internal_displacement_qs.aggregate(
            models.Sum("new_displacement"),
        )

        conflict_total_displacement_countries = (
            conflict_total_displacement_qs.order_by().values_list("iso3", flat=True).distinct()
        )
        conflict_internal_displacement_countries = (
            conflict_internal_displacement_qs.order_by().values_list("iso3", flat=True).distinct()
        )

        total_displacements = (disaster_total_displacement_stats["total_displacement__sum"] or 0) + (
            conflict_total_displacement_stats["total_displacement__sum"] or 0
        )
        internal_displacements = (disaster_internal_displacement_stats["new_displacement__sum"] or 0) + (
            conflict_internal_displacement_stats["new_displacement__sum"] or 0
        )

        return GiddCombinedStatisticsType(
            internal_displacements=internal_displacements,
            total_displacements=total_displacements,
            internal_displacements_rounded=round_and_remove_zero(internal_displacements),
            total_displacements_rounded=round_and_remove_zero(total_displacements),
            internal_displacement_countries=len(
                set(
                    [
                        *disaster_internal_displacement_countries,
                        *conflict_internal_displacement_countries,
                    ]
                )
            ),
            total_displacement_countries=len(
                set(
                    [
                        *disaster_total_displacement_countries,
                        *conflict_total_displacement_countries,
                    ]
                )
            ),
        )

    @staticmethod
    def resolve_gidd_public_country_displacements(parent, info, **kwargs):
        client_id = kwargs.pop("client_id")
        track_gidd(client_id, ExternalApiDump.ExternalApiType.GIDD_COUNTRY_DISPLACEMENT_GRAPHQL)

        conflict_filter, disaster_filter = cause_typology_filters(kwargs)

        qs = GiddCountryDisplacementFilter(data=kwargs).qs

        # new_displacement is a flow, so it sums across the whole window. total_displacement is
        # IDP stock (point-in-time), so it is confined to a single year: end_year, or the
        # (pre-)release year when end_year is omitted.
        end_year = resolve_stock_year(kwargs, kwargs.get("end_year"))
        conflict_stock_year = end_year
        disaster_stock_year = end_year

        rows = (
            qs.values("iso3", "country_name", "country_id")
            .annotate(
                conflict_new_displacement=Coalesce(models.Sum("new_displacement", filter=conflict_filter), 0),
                conflict_total_displacement=Coalesce(
                    models.Sum("total_displacement", filter=conflict_filter & idp_stock_filter(conflict_stock_year)), 0
                ),
                disaster_new_displacement=Coalesce(models.Sum("new_displacement", filter=disaster_filter), 0),
                disaster_total_displacement=Coalesce(
                    models.Sum("total_displacement", filter=disaster_filter & idp_stock_filter(disaster_stock_year)), 0
                ),
            )
            .filter(
                Q(conflict_new_displacement__gt=0)
                | Q(conflict_total_displacement__gt=0)
                | Q(disaster_new_displacement__gt=0)
                | Q(disaster_total_displacement__gt=0)
            )
            .order_by("iso3")
        )

        return [
            GiddCountryDisplacementType(
                iso3=row["iso3"],
                country_name=row["country_name"],
                country_id=row["country_id"],
                conflict_new_displacement=row["conflict_new_displacement"] or None,
                conflict_new_displacement_rounded=round_and_remove_zero(row["conflict_new_displacement"]),
                conflict_total_displacement=row["conflict_total_displacement"] or None,
                conflict_total_displacement_rounded=round_and_remove_zero(row["conflict_total_displacement"]),
                disaster_new_displacement=row["disaster_new_displacement"] or None,
                disaster_new_displacement_rounded=round_and_remove_zero(row["disaster_new_displacement"]),
                disaster_total_displacement=row["disaster_total_displacement"] or None,
                disaster_total_displacement_rounded=round_and_remove_zero(row["disaster_total_displacement"]),
            )
            for row in rows
        ]

    @staticmethod
    def resolve_gidd_public_country_year_displacements(parent, info, **kwargs):
        client_id = kwargs.pop("client_id")
        track_gidd(client_id, ExternalApiDump.ExternalApiType.GIDD_COUNTRY_YEAR_DISPLACEMENT_GRAPHQL)

        conflict_filter, disaster_filter = cause_typology_filters(kwargs)
        page = max(1, kwargs.pop("page", None) or 1)
        page_size = get_page_size(kwargs.pop("page_size", None) or GIDD_COUNTRY_YEAR_DEFAULT_PAGE_SIZE)
        ordering = kwargs.pop("ordering", None)

        # NULLS LAST throughout. The tiebreak is appended below instead, once the grouped queryset
        # exists for `tiebreak_fields` to derive it from.
        order_by = []
        ordered_columns = []
        for token in (ordering or "").replace(" ", "").split(","):
            if not token:
                continue
            descending = token.startswith("-")
            key = to_snake_case(strip_direction(token))
            if key not in GIDD_COUNTRY_YEAR_SORTABLE:
                raise ValueError(f"Invalid ordering field: {key}")
            ordered_columns.append(key)
            order_by.append(models.F(key).desc(nulls_last=True) if descending else models.F(key).asc(nulls_last=True))
        qs = GiddCountryDisplacementFilter(data=kwargs).qs

        rows = (
            qs.values("iso3", "country_name", "country_id", "year")
            .annotate(
                conflict_new_displacement=Coalesce(models.Sum("new_displacement", filter=conflict_filter), 0),
                conflict_total_displacement=Coalesce(models.Sum("total_displacement", filter=conflict_filter), 0),
                disaster_new_displacement=Coalesce(models.Sum("new_displacement", filter=disaster_filter), 0),
                disaster_total_displacement=Coalesce(models.Sum("total_displacement", filter=disaster_filter), 0),
            )
            .filter(
                Q(conflict_new_displacement__gt=0)
                | Q(conflict_total_displacement__gt=0)
                | Q(disaster_new_displacement__gt=0)
                | Q(disaster_total_displacement__gt=0)
            )
        )

        for tiebreak in tiebreak_fields(rows, ordered_columns):
            order_by.append(models.F(tiebreak).asc(nulls_last=True))
        rows = rows.order_by(*order_by)

        offset = (page - 1) * page_size
        return GiddCountryYearDisplacementListType(
            total_count=rows.count(),
            page=page,
            page_size=page_size,
            results=[
                GiddCountryYearDisplacementType(
                    iso3=row["iso3"],
                    country_name=row["country_name"],
                    country_id=row["country_id"],
                    year=row["year"],
                    conflict_new_displacement=row["conflict_new_displacement"] or None,
                    conflict_new_displacement_rounded=round_and_remove_zero(row["conflict_new_displacement"]),
                    conflict_total_displacement=row["conflict_total_displacement"] or None,
                    conflict_total_displacement_rounded=round_and_remove_zero(row["conflict_total_displacement"]),
                    disaster_new_displacement=row["disaster_new_displacement"] or None,
                    disaster_new_displacement_rounded=round_and_remove_zero(row["disaster_new_displacement"]),
                    disaster_total_displacement=row["disaster_total_displacement"] or None,
                    disaster_total_displacement_rounded=round_and_remove_zero(row["disaster_total_displacement"]),
                )
                for row in rows[offset : offset + page_size]
            ],
        )
