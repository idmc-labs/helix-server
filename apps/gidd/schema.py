# types.py
import graphene
from graphene_django_extras import DjangoObjectField
from graphene_django.filter.utils import get_filtering_args_from_filterset
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.pagination import PageGraphqlPaginationWithoutCount
from utils.graphene.enums import EnumDescription
from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.entry.enums import FigureCategoryTypeEnum
from utils.common import round_and_remove_zero, track_gidd
from apps.entry.models import ExternalApiDump

from django.db import models
from django.db.models.functions import Coalesce
from .models import (
    Conflict,
    Disaster,
    StatusLog,
    ReleaseMetadata,
    PublicFigureAnalysis,
    DisplacementData,
)
from apps.country.models import Country
from graphene_django import DjangoObjectType
from .filters import (
    ConflictFilter,
    DisasterFilter,
    ConflictStatisticsFilter,
    DisasterStatisticsFilter,
    GiddStatusLogFilter,
    PublicFigureAnalysisFilter,
    DisplacementDataFilter,
    ReleaseMetadataFilter,
)
from .enums import GiddStatusLogEnum


def custom_date_filters(start_year, end_year):
    filters = {
        'idps_date_filters': dict(),
        'nd_date_filters': dict(),
    }

    filters['idps_date_filters'].update({'total_displacement__gt': 0})
    filters['nd_date_filters'].update({'new_displacement__gt': 0})

    if start_year:
        filters['nd_date_filters'].update({'year__gte': start_year})
    if end_year:
        filters['nd_date_filters'].update({'year__lte': end_year})
        filters['idps_date_filters'].update({'year__gte': end_year})
        filters['idps_date_filters'].update({'year__lte': end_year})
    return filters


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


class GiddConflictStatisticsType(graphene.ObjectType):
    new_displacements = graphene.Int()
    new_displacements_rounded = graphene.Int()
    total_displacements = graphene.Int()
    total_displacements_rounded = graphene.Int()
    total_displacement_countries = graphene.Int()
    internal_displacement_countries = graphene.Int()
    new_displacement_timeseries_by_year = graphene.List(
        graphene.NonNull(GiddTimeSeriesStatisticsByYearType)
    )
    new_displacement_timeseries_by_country = graphene.List(
        graphene.NonNull(GiddTimeSeriesStatisticsByCountryType)
    )
    total_displacement_timeseries_by_year = graphene.List(
        graphene.NonNull(GiddTimeSeriesStatisticsByYearType)
    )
    total_displacement_timeseries_by_country = graphene.List(
        graphene.NonNull(GiddTimeSeriesStatisticsByCountryType)
    )


class GiddDisasterStatisticsType(graphene.ObjectType):
    new_displacements = graphene.Int()
    new_displacements_rounded = graphene.Int()
    total_events = graphene.Int()
    displacements_by_hazard_type = graphene.List(graphene.NonNull(DisplacementByHazardType))

    total_displacement_countries = graphene.Int()
    internal_displacement_countries = graphene.Int()
    total_displacements = graphene.Int()
    total_displacements_rounded = graphene.Int()

    new_displacement_timeseries_by_year = graphene.List(
        graphene.NonNull(GiddTimeSeriesStatisticsByYearType)
    )
    new_displacement_timeseries_by_country = graphene.List(
        graphene.NonNull(GiddTimeSeriesStatisticsByCountryType)
    )
    total_displacement_timeseries_by_year = graphene.List(
        graphene.NonNull(GiddTimeSeriesStatisticsByYearType)
    )
    total_displacement_timeseries_by_country = graphene.List(
        graphene.NonNull(GiddTimeSeriesStatisticsByCountryType)
    )


class GiddCombinedStatisticsType(graphene.ObjectType):
    internal_displacements = graphene.Int()
    total_displacements = graphene.Int()
    internal_displacements_rounded = graphene.Int()
    total_displacements_rounded = graphene.Int()
    internal_displacement_countries = graphene.Int()
    total_displacement_countries = graphene.Int()


class GiddConflictType(DjangoObjectType):
    country_id = graphene.ID(required=True)

    class Meta:
        model = Conflict
        fields = (
            'id',
            'iso3',
            'country_name',
            'year',
            'new_displacement',
            'total_displacement',
            'new_displacement_rounded',
            'total_displacement_rounded',
        )

    @staticmethod
    def resolve_country_id(root, info, **kwargs):
        return root.country_id


class GiddConflictListType(CustomDjangoListObjectType):
    class Meta:
        model = Conflict
        filterset_class = ConflictFilter


class GiddDisasterType(DjangoObjectType):
    country_id = graphene.ID(required=True)
    event_id = graphene.ID()
    hazard_category_id = graphene.ID()
    hazard_sub_category_id = graphene.ID()
    hazard_type_id = graphene.ID()
    hazard_sub_type_id = graphene.ID()

    class Meta:
        model = Disaster
        fields = (
            'id',
            'year',
            'start_date',
            'start_date_accuracy',
            'end_date',
            'end_date_accuracy',
            'new_displacement',
            'total_displacement',
            'new_displacement_rounded',
            'total_displacement_rounded',
            'event_name',
            'iso3',
            'country_name',
            'hazard_category_name',
            'hazard_sub_category_name',
            'hazard_type_name',
            'hazard_sub_type_name',
            'event_codes',
            'event_codes_type',
        )

    @staticmethod
    def resolve_country_id(root, info, **kwargs):
        return root.country_id

    @staticmethod
    def resolve_event_id(root, info, **kwargs):
        return root.event_id

    @staticmethod
    def resolve_hazard_category_id(root, info, **kwargs):
        return root.hazard_category_id

    @staticmethod
    def resolve_hazard_sub_category_id(root, info, **kwargs):
        return root.hazard_sub_category_id

    @staticmethod
    def resolve_hazard_type_id(root, info, **kwargs):
        return root.hazard_type_id

    @staticmethod
    def resolve_hazard_sub_type_id(root, info, **kwargs):
        return root.hazard_sub_type_id


class GiddDisasterListType(CustomDjangoListObjectType):
    class Meta:
        model = Disaster
        filterset_class = DisasterFilter


class GiddStatusLogType(DjangoObjectType):
    class Meta:
        model = StatusLog
    status = graphene.Field(GiddStatusLogEnum)
    status_display = EnumDescription(source='get_status_display')


class GiddStatusLogListType(CustomDjangoListObjectType):
    class Meta:
        model = StatusLog
        filterset_class = GiddStatusLogFilter


class GiddPublicFigureAnalysisType(DjangoObjectType):
    class Meta:
        model = PublicFigureAnalysis
        fields = (
            'id',
            'iso3',
            'year',
            'figures',
            'figures_rounded',
            'description',
        )

    figure_cause = graphene.Field(CrisisTypeGrapheneEnum)
    figure_cause_display = EnumDescription(source='get_figure_cause_display')
    figure_category = graphene.Field(FigureCategoryTypeEnum)
    figure_category_display = EnumDescription(source='get_figure_category_display')


class GiddPublicFigureAnalysisListType(CustomDjangoListObjectType):
    class Meta:
        model = PublicFigureAnalysis
        filterset_class = PublicFigureAnalysisFilter


class GiddReleaseMetadataType(DjangoObjectType):
    class Meta:
        model = ReleaseMetadata


class GiddPublicCountryRegionType(graphene.ObjectType):
    id = graphene.ID(required=True)
    name = graphene.String(required=True)


class GiddPublicCountryType(graphene.ObjectType):
    id = graphene.ID(required=True)
    iso3 = graphene.String(required=True)
    idmc_short_name = graphene.String(required=True)
    region = graphene.Field(GiddPublicCountryRegionType)


class GiddHazardType(graphene.ObjectType):
    id = graphene.ID(required=True)
    name = graphene.String(required=True)


class GiddHazardSubCategoryType(graphene.ObjectType):
    id = graphene.ID(required=True)
    name = graphene.String(required=True)


class GiddDisplacementDataType(DjangoObjectType):
    class Meta:
        model = DisplacementData
        fields = (
            'id',
            'iso3',
            'country_name',
            'year',
            'conflict_total_displacement',
            'conflict_new_displacement',
            'disaster_new_displacement',
            'disaster_total_displacement',
            'conflict_total_displacement_rounded',
            'conflict_new_displacement_rounded',
            'disaster_new_displacement_rounded',
            'disaster_total_displacement_rounded',
        )


class GiddDisplacementDataListType(CustomDjangoListObjectType):
    class Meta:
        model = DisplacementData
        filterset_class = DisplacementDataFilter


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


class Query(graphene.ObjectType):
    gidd_public_conflicts = DjangoPaginatedListObjectField(
        GiddConflictListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
        client_id=graphene.String(required=True)
    )
    gidd_public_disasters = DjangoPaginatedListObjectField(
        GiddDisasterListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
        client_id=graphene.String(required=True),
    )
    gidd_public_conflict_statistics = graphene.Field(
        GiddConflictStatisticsType,
        **get_filtering_args_from_filterset(
            ConflictStatisticsFilter, GiddConflictStatisticsType
        ),
        required=True,
        client_id=graphene.String(required=True),
    )
    gidd_public_disaster_statistics = graphene.Field(
        GiddDisasterStatisticsType,
        **get_filtering_args_from_filterset(
            DisasterStatisticsFilter, GiddDisasterStatisticsType
        ),
        required=True,
        client_id=graphene.String(required=True),
    )
    gidd_log = DjangoObjectField(
        GiddStatusLogType,
    )
    gidd_logs = DjangoPaginatedListObjectField(
        GiddStatusLogListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
    )
    gidd_public_release_meta_data = graphene.Field(
        GiddReleaseMetadataType,
        client_id=graphene.String(required=True),
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
    gidd_public_figure_analysis_list = DjangoPaginatedListObjectField(
        GiddPublicFigureAnalysisListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
        client_id=graphene.String(required=True),
    )
    gidd_public_displacements = DjangoPaginatedListObjectField(
        GiddDisplacementDataListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
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
        **get_filtering_args_from_filterset(
            ReleaseMetadataFilter, GiddEventType
        ),
        client_id=graphene.String(required=True),
    )
    gidd_public_combined_statistics = graphene.Field(
        GiddCombinedStatisticsType,
        **get_filtering_args_from_filterset(
            DisasterStatisticsFilter, GiddCombinedStatisticsType
        ),
        required=True,
        client_id=graphene.String(required=True),
    )

    @staticmethod
    def resolve_gidd_public_release_meta_data(parent, info, **kwargs):
        # Track
        client_id = kwargs.pop('client_id')
        track_gidd(client_id, ExternalApiDump.ExternalApiType.GIDD_RELEASE_META_DATA_GRAPHQL)

        return ReleaseMetadata.objects.last()

    @staticmethod
    def resolve_gidd_release_meta_data(parent, info, **kwargs):
        return ReleaseMetadata.objects.last()

    @staticmethod
    def resolve_gidd_public_countries(parent, info, **kwargs):
        # Track
        client_id = kwargs.pop('client_id')
        track_gidd(client_id, ExternalApiDump.ExternalApiType.GIDD_PUBLIC_COUNTRIES_GRAPHQL)

        return [
            GiddPublicCountryType(
                id=country['id'],
                iso3=country['iso3'],
                idmc_short_name=country['idmc_short_name'],
                region=GiddPublicCountryRegionType(
                    id=country['region__id'],
                    name=country['region__name'],
                )
            ) for country in Country.objects.values(
                'id', 'idmc_short_name', 'iso3', 'region__id', 'region__name'
            )
        ]

    @staticmethod
    def resolve_gidd_public_conflict_statistics(parent, info, **kwargs):
        # Track
        client_id = kwargs.pop('client_id')
        track_gidd(client_id, ExternalApiDump.ExternalApiType.GIDD_CONFLICT_STAT_GRAPHQL)

        conflict_qs = ConflictStatisticsFilter(data=kwargs).qs
        start_year = kwargs.pop('start_year', None)
        end_year = kwargs.pop('end_year', None)
        filters = custom_date_filters(start_year, end_year)

        conflict_total_displacement_qs = ConflictStatisticsFilter(data=kwargs).qs.filter(
            **filters.get('idps_date_filters')
        )
        conflict_new_displacement_qs = ConflictStatisticsFilter(data=kwargs).qs.filter(
            **filters.get('nd_date_filters')
        )

        new_displacement_timeseries_by_year_qs = conflict_qs.filter(new_displacement__gt=0).values('year').annotate(
            total=Coalesce(models.Sum('new_displacement', output_field=models.IntegerField()), 0)
        ).order_by('year').values('year', 'total')

        new_displacement_timeseries_by_country_qs = conflict_qs.filter(new_displacement__gt=0).values('year').annotate(
            total=Coalesce(models.Sum('new_displacement', output_field=models.IntegerField()), 0)
        ).order_by('year').values('year', 'total', 'country_id', 'country_name', 'iso3')

        total_displacement_timeseries_by_year_qs = conflict_qs.filter(total_displacement__gt=0).values('year').annotate(
            total=Coalesce(models.Sum('total_displacement', output_field=models.IntegerField()), 0)
        ).order_by('year').values('year', 'total')

        total_displacement_timeseries_by_country_qs = conflict_qs.filter(total_displacement__gt=0).values('year').annotate(
            total=Coalesce(models.Sum('total_displacement', output_field=models.IntegerField()), 0)
        ).order_by('year').values('year', 'total', 'country_id', 'country_name', 'iso3')

        return GiddConflictStatisticsType(
            new_displacements_rounded=round_and_remove_zero(
                conflict_new_displacement_qs.aggregate(
                    total=Coalesce(models.Sum('new_displacement', output_field=models.IntegerField()), 0)
                )['total']
            ),
            new_displacements=conflict_new_displacement_qs.aggregate(
                total=Coalesce(models.Sum('new_displacement', output_field=models.IntegerField()), 0)
            )['total'],

            total_displacements_rounded=round_and_remove_zero(
                conflict_total_displacement_qs.aggregate(
                    total=Coalesce(models.Sum('total_displacement', output_field=models.IntegerField()), 0)
                )['total']
            ),
            total_displacements=conflict_total_displacement_qs.aggregate(
                total=Coalesce(models.Sum('total_displacement', output_field=models.IntegerField()), 0)
            )['total'],
            total_displacement_countries=conflict_total_displacement_qs.distinct('iso3').count(),
            internal_displacement_countries=conflict_new_displacement_qs.distinct('iso3').count(),
            new_displacement_timeseries_by_year=[
                GiddTimeSeriesStatisticsByYearType(
                    year=item['year'],
                    total=item['total'],
                    total_rounded=round_and_remove_zero(item['total']),
                ) for item in new_displacement_timeseries_by_year_qs
            ],
            new_displacement_timeseries_by_country=[
                GiddTimeSeriesStatisticsByCountryType(
                    year=item['year'],
                    total_rounded=round_and_remove_zero(item['total']),
                    total=item['total'],
                    country=GiddDisasterCountryType(
                        id=item['country_id'],
                        iso3=item['iso3'],
                        country_name=item['country_name']
                    )
                ) for item in new_displacement_timeseries_by_country_qs
            ],
            total_displacement_timeseries_by_year=[
                GiddTimeSeriesStatisticsByYearType(
                    year=item['year'],
                    total=item['total'],
                    total_rounded=round_and_remove_zero(item['total']),
                ) for item in total_displacement_timeseries_by_year_qs
            ],
            total_displacement_timeseries_by_country=[
                GiddTimeSeriesStatisticsByCountryType(
                    year=item['year'],
                    total_rounded=round_and_remove_zero(item['total']),
                    total=item['total'],
                    country=GiddDisasterCountryType(
                        id=item['country_id'],
                        iso3=item['iso3'],
                        country_name=item['country_name']
                    )
                ) for item in total_displacement_timeseries_by_country_qs
            ],
        )

    @staticmethod
    def resolve_gidd_public_disaster_statistics(parent, info, **kwargs):
        # Track
        client_id = kwargs.pop('client_id')
        track_gidd(client_id, ExternalApiDump.ExternalApiType.GIDD_DISASTER_STAT_GRAPHQL)

        disaster_qs = DisasterStatisticsFilter(data=kwargs).qs
        start_year = kwargs.pop('start_year', None)
        end_year = kwargs.pop('end_year', None)
        filters = custom_date_filters(start_year, end_year)

        disaster_total_displacement_qs = DisasterStatisticsFilter(data=kwargs).qs.filter(
            **filters.get('idps_date_filters')
        )
        disaster_new_displacement_qs = DisasterStatisticsFilter(data=kwargs).qs.filter(
            **filters.get('nd_date_filters')
        )

        new_displacement_timeseries_by_year_qs = disaster_qs.filter(new_displacement__gt=0).values('year').annotate(
            total=Coalesce(models.Sum('new_displacement', output_field=models.IntegerField()), 0)
        ).order_by('year').values('year', 'total')

        new_displacement_timeseries_by_country_qs = disaster_qs.filter(new_displacement__gt=0).values('year').annotate(
            total=Coalesce(models.Sum('new_displacement', output_field=models.IntegerField()), 0)
        ).order_by('year').values('year', 'total', 'country_id', 'country_name', 'iso3')

        total_displacement_timeseries_by_year_qs = disaster_qs.filter(total_displacement__gt=0).values('year').annotate(
            total=Coalesce(models.Sum('total_displacement', output_field=models.IntegerField()), 0)
        ).order_by('year').values('year', 'total')

        total_displacement_timeseries_by_country_qs = disaster_qs.filter(total_displacement__gt=0).values('year').annotate(
            total=Coalesce(models.Sum('total_displacement', output_field=models.IntegerField()), 0)
        ).order_by('year').values('year', 'total', 'country_id', 'country_name', 'iso3')

        categories_qs = disaster_qs.values('hazard_type', 'hazard_type__id').annotate(
            total=Coalesce(models.Sum('new_displacement', output_field=models.IntegerField()), 0),
            label=models.Case(
                models.When(hazard_sub_category=None, then=models.Value('Not labeled')),
                default=models.F('hazard_type_name'),
                output_field=models.CharField()
            )
        ).filter(total__gt=0)

        return GiddDisasterStatisticsType(
            new_displacements_rounded=round_and_remove_zero(
                disaster_new_displacement_qs.aggregate(
                    total=Coalesce(models.Sum('new_displacement', output_field=models.IntegerField()), 0)
                )['total']
            ),
            new_displacements=disaster_new_displacement_qs.aggregate(
                total=Coalesce(models.Sum('new_displacement', output_field=models.IntegerField()), 0)
            )['total'],
            total_displacements_rounded=round_and_remove_zero(
                disaster_total_displacement_qs.aggregate(
                    total=Coalesce(models.Sum('total_displacement', output_field=models.IntegerField()), 0)
                )['total']
            ),
            total_displacements=disaster_total_displacement_qs.aggregate(
                total=Coalesce(models.Sum('total_displacement', output_field=models.IntegerField()), 0)
            )['total'],
            total_events=disaster_new_displacement_qs.filter(
                models.Q(new_displacement__gt=0) | models.Q(total_displacement__gt=0)
            ).values('event__name').annotate(
                events=models.Count('id')
            ).aggregate(total_events=Coalesce(models.Sum('events', output_field=models.IntegerField()), 0))['total_events'],

            total_displacement_countries=disaster_total_displacement_qs.distinct('iso3').count(),
            internal_displacement_countries=disaster_new_displacement_qs.distinct('iso3').count(),

            new_displacement_timeseries_by_year=[
                GiddTimeSeriesStatisticsByYearType(
                    year=item['year'],
                    total_rounded=round_and_remove_zero(item['total']),
                    total=item['total'],
                ) for item in new_displacement_timeseries_by_year_qs
            ],

            new_displacement_timeseries_by_country=[
                GiddTimeSeriesStatisticsByCountryType(
                    year=item['year'],
                    total_rounded=round_and_remove_zero(item['total']),
                    total=item['total'],
                    country=GiddDisasterCountryType(
                        id=item['country_id'],
                        iso3=item['iso3'],
                        country_name=item['country_name']
                    )
                ) for item in new_displacement_timeseries_by_country_qs
            ],
            total_displacement_timeseries_by_year=[
                GiddTimeSeriesStatisticsByYearType(
                    year=item['year'],
                    total_rounded=round_and_remove_zero(item['total']),
                    total=item['total'],
                ) for item in total_displacement_timeseries_by_year_qs
            ],

            total_displacement_timeseries_by_country=[
                GiddTimeSeriesStatisticsByCountryType(
                    year=item['year'],
                    total=item['total'],
                    total_rounded=round_and_remove_zero(item['total']),
                    country=GiddDisasterCountryType(
                        id=item['country_id'],
                        iso3=item['iso3'],
                        country_name=item['country_name']
                    )
                ) for item in total_displacement_timeseries_by_country_qs
            ],

            displacements_by_hazard_type=[
                DisplacementByHazardType(
                    id=item['hazard_type__id'],
                    label=item['label'],
                    new_displacements=item['total'],
                    new_displacements_rounded=round_and_remove_zero(item['total']),
                ) for item in categories_qs
            ]
        )

    @staticmethod
    def resolve_gidd_public_hazard_types(parent, info, **kwargs):
        # Track
        client_id = kwargs.pop('client_id')
        track_gidd(client_id, ExternalApiDump.ExternalApiType.GIDD_HAZARD_TYPES_GRAPHQL)

        return [
            GiddHazardType(
                id=hazard['hazard_type__id'],
                name=hazard['hazard_type__name'],

            ) for hazard in Disaster.objects.values(
                'hazard_type__id', 'hazard_type__name'
            ).distinct(
                'hazard_type__id', 'hazard_type__name'
            )
        ]

    @staticmethod
    def resolve_gidd_public_year(parent, info, **kwargs):
        # Track
        client_id = kwargs.pop('client_id')
        track_gidd(client_id, ExternalApiDump.ExternalApiType.GIDD_YEAR_GRAPHQL)

        gidd_meta_data = ReleaseMetadata.objects.last()
        if kwargs['release_environment'].lower() == ReleaseMetadata.ReleaseEnvironment.PRE_RELEASE.name.lower():
            return GiddYearType(year=gidd_meta_data.pre_release_year)
        if kwargs['release_environment'].lower() == ReleaseMetadata.ReleaseEnvironment.RELEASE.name.lower():
            return GiddYearType(year=gidd_meta_data.release_year)

    @staticmethod
    def resolve_gidd_public_event(parent, info, **kwargs):
        # Track
        client_id = kwargs.pop('client_id')
        track_gidd(client_id, ExternalApiDump.ExternalApiType.GIDD_EVENT_GRAPHQL)

        event_id = kwargs['event_id']
        disaster_qs = DisasterFilter(data=kwargs).qs.filter(event_id=event_id)

        if not disaster_qs.exists():
            return None

        # NOTE:- There is always one object after group by event_name attrs
        # so first objects is taken directly from queryset instead of iterating
        event_data = disaster_qs.values(
            'event_name',
            'start_date',
            'end_date',
            'event_codes',
            'event_codes_type',
        ).order_by().annotate(
            total_new_displacement=models.Sum('new_displacement'),
        )[0]

        affected_countries_qs = disaster_qs.values(
            'country_name',
            'iso3',
        ).order_by().annotate(
            total_new_displacement=models.Sum('new_displacement'),
        )

        hazard_types_qs = disaster_qs.values(
            'hazard_type_id', 'hazard_type__name'
        ).distinct(
            'hazard_type_id', 'hazard_type__name'
        )
        return GiddEventType(
            event_name=event_data.get('event_name'),
            new_displacement_rounded=round_and_remove_zero(event_data.get('total_new_displacement')),
            new_displacement=event_data.get('total_new_displacement'),
            start_date=event_data.get('start_date'),
            end_date=event_data.get('end_date'),
            event_codes=event_data.get('event_codes'),
            event_codes_type=event_data.get('event_codes_type'),
            affected_countries=[
                GiddEventAffectedCountryType(
                    iso3=country_data['iso3'],
                    country_name=country_data['country_name'],
                    new_displacement_rounded=round_and_remove_zero(country_data['total_new_displacement']),
                    new_displacement=country_data['total_new_displacement'],
                ) for country_data in affected_countries_qs
            ],
            hazard_types=[
                GiddHazardType(
                    id=hazard_type['hazard_type_id'],
                    name=hazard_type['hazard_type__name'],
                ) for hazard_type in hazard_types_qs
            ],
        )

    @staticmethod
    def resolve_gidd_public_combined_statistics(parent, info, **kwargs):
        # Track
        client_id = kwargs.pop('client_id')
        track_gidd(client_id, ExternalApiDump.ExternalApiType.GIDD_COMBINED_STAT_GRAPHQL)

        start_year = kwargs.pop('start_year', None)
        end_year = kwargs.pop('end_year', None)

        filters = custom_date_filters(start_year, end_year)

        disaster_total_displacement_qs = DisasterStatisticsFilter(data=kwargs).qs.filter(
            **filters.get('idps_date_filters')
        )
        disaster_internal_displacement_qs = DisasterStatisticsFilter(data=kwargs).qs.filter(
            **filters.get('nd_date_filters')
        )

        disaster_total_displacement_stats = disaster_total_displacement_qs.aggregate(
            models.Sum('total_displacement'),
        )
        disaster_internal_displacement_stats = disaster_internal_displacement_qs.aggregate(
            models.Sum('new_displacement'),
        )

        disaster_total_displacement_countries = disaster_total_displacement_qs.order_by()\
            .values_list('iso3', flat=True).distinct()
        disaster_internal_displacement_countries = disaster_internal_displacement_qs.order_by()\
            .values_list('iso3', flat=True).distinct()

        # Conflict doesn't has hazard_type
        if kwargs.get('hazard_type'):
            kwargs = kwargs.pop('hazard_type')

        conflict_total_displacement_qs = ConflictStatisticsFilter(data=kwargs).qs.filter(
            **filters.get('idps_date_filters')
        )
        conflict_internal_displacement_qs = ConflictStatisticsFilter(data=kwargs).qs.filter(
            **filters.get('nd_date_filters')
        )

        conflict_total_displacement_stats = conflict_total_displacement_qs.aggregate(
            models.Sum('total_displacement'),
        )
        conflict_internal_displacement_stats = conflict_internal_displacement_qs.aggregate(
            models.Sum('new_displacement'),
        )

        conflict_total_displacement_countries = conflict_total_displacement_qs.order_by()\
            .values_list('iso3', flat=True).distinct()
        conflict_internal_displacement_countries = conflict_internal_displacement_qs.order_by()\
            .values_list('iso3', flat=True).distinct()

        total_displacements = (
            (disaster_total_displacement_stats['total_displacement__sum'] or 0) +
            (conflict_total_displacement_stats['total_displacement__sum'] or 0)
        )
        internal_displacements = (
            (disaster_internal_displacement_stats['new_displacement__sum'] or 0) +
            (conflict_internal_displacement_stats['new_displacement__sum'] or 0)
        )

        return GiddCombinedStatisticsType(
            internal_displacements=internal_displacements,
            total_displacements=total_displacements,
            internal_displacements_rounded=round_and_remove_zero(
                internal_displacements
            ),
            total_displacements_rounded=round_and_remove_zero(
                total_displacements
            ),
            internal_displacement_countries=len(set([
                *disaster_internal_displacement_countries,
                *conflict_internal_displacement_countries,
            ])),
            total_displacement_countries=len(set([
                *disaster_total_displacement_countries,
                *conflict_total_displacement_countries,
            ])),
        )
