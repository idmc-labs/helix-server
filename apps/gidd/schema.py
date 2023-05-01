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
)
from .enums import GiddStatusLogEnum


class GiddTimeSeriesStatisticsType(graphene.ObjectType):
    year = graphene.Int(required=True)
    total = graphene.Int()


class GiddDisasterCountryType(graphene.ObjectType):
    id = graphene.Int(required=True)
    iso3 = graphene.String(required=True)
    country_name = graphene.String(required=True)


class GiddDisasterTimeSeriesStatisticsType(graphene.ObjectType):
    year = graphene.String(required=True)
    total = graphene.Int()
    country = graphene.Field(GiddDisasterCountryType, required=True)


class GiddCategoryStatisticsType(graphene.ObjectType):
    label = graphene.String(required=True)
    total = graphene.Int()


class GiddConflictStatisticsType(graphene.ObjectType):
    new_displacements = graphene.Int()
    total_idps = graphene.Int()
    new_displacement_timeseries = graphene.List(graphene.NonNull(GiddTimeSeriesStatisticsType))
    idps_timeseries = graphene.List(graphene.NonNull(GiddTimeSeriesStatisticsType))


class GiddDisasterStatisticsType(graphene.ObjectType):
    new_displacements = graphene.Int()
    total_events = graphene.Int()
    timeseries = graphene.List(graphene.NonNull(GiddDisasterTimeSeriesStatisticsType))
    categories = graphene.List(graphene.NonNull(GiddCategoryStatisticsType))


class GiddConflictType(DjangoObjectType):
    class Meta:
        model = Conflict


class GiddConflictListType(CustomDjangoListObjectType):
    class Meta:
        model = Conflict
        filterset_class = ConflictFilter


class GiddDisasterType(DjangoObjectType):
    class Meta:
        model = Disaster


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
            'iso3',
            'year',
            'figures',
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


class GiddHazardSubType(graphene.ObjectType):
    id = graphene.ID(required=True)
    name = graphene.String(required=True)


class GiddHazardSubCategoryType(graphene.ObjectType):
    id = graphene.ID(required=True)
    name = graphene.String(required=True)


class GiddDisplacementDataType(DjangoObjectType):
    disaster_total_idps = graphene.Int()
    disaster_total_nd = graphene.Int()

    class Meta:
        model = DisplacementData
        fields = (
            'id',
            'iso3',
            'country_name',
            'year',
            'conflict_total_nd',
            'conflict_total_idps',
        )

    cause = graphene.Field(CrisisTypeGrapheneEnum)
    cause_display = EnumDescription(source='get_cause_display')


class GiddDisplacementDataListType(CustomDjangoListObjectType):
    class Meta:
        model = DisplacementData
        filterset_class = DisplacementDataFilter


class GiddYearType(graphene.ObjectType):
    year = graphene.Int(required=True)


class Query(graphene.ObjectType):
    gidd_conflict = DjangoObjectField(GiddConflictType)
    gidd_conflicts = DjangoPaginatedListObjectField(
        GiddConflictListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        )
    )
    gidd_disaster = DjangoObjectField(GiddDisasterType)
    gidd_disasters = DjangoPaginatedListObjectField(
        GiddDisasterListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        )
    )
    gidd_conflict_statistics = graphene.Field(
        GiddConflictStatisticsType,
        **get_filtering_args_from_filterset(
            ConflictStatisticsFilter, GiddConflictStatisticsType
        ),
        required=True,
    )
    gidd_disaster_statistics = graphene.Field(
        GiddDisasterStatisticsType,
        **get_filtering_args_from_filterset(
            DisasterStatisticsFilter, GiddDisasterStatisticsType
        ),
        required=True,
    )
    gidd_log = DjangoObjectField(GiddStatusLogType)
    gidd_logs = DjangoPaginatedListObjectField(
        GiddStatusLogListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        )
    )
    gidd_release_meta_data = graphene.Field(GiddReleaseMetadataType)
    gidd_public_countries = graphene.List(graphene.NonNull(GiddPublicCountryType))
    gidd_hazard_sub_types = graphene.List(GiddHazardSubType)
    gidd_public_figure_analysis = DjangoObjectField(GiddPublicFigureAnalysisType)
    gidd_public_figure_analysis_list = DjangoPaginatedListObjectField(
        GiddPublicFigureAnalysisListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        )
    )
    gidd_displacement = DjangoObjectField(GiddDisplacementDataType)
    gidd_displacements = DjangoPaginatedListObjectField(
        GiddDisplacementDataListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        )
    )
    gidd_year = graphene.Field(
        graphene.NonNull(GiddYearType), release_environment=graphene.String(required=True)
    )

    @staticmethod
    def resolve_gidd_release_meta_data(parent, info, **kwargs):
        return ReleaseMetadata.objects.last()

    @staticmethod
    def resolve_gidd_public_country_list(parent, info, **kwargs):
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
    def resolve_gidd_conflict_statistics(parent, info, **kwargs):
        conflict_qs = ConflictStatisticsFilter(data=kwargs).qs
        new_displacement_timeseries_qs = conflict_qs.filter(
            new_displacement__gt=0
        ).values('year').annotate(
            total=models.Sum('new_displacement', output_field=models.IntegerField()),
        ).order_by('year').values('year', 'total')

        idps_timeseries_qs = conflict_qs.filter(
            total_displacement__isnull=False
        ).values('year').annotate(
            total=models.Sum('total_displacement', output_field=models.IntegerField())
        ).order_by('year').values('year', 'total')
        total_idps = conflict_qs.order_by('-year').first().total_displacement if conflict_qs.order_by('-year') else 0

        return GiddConflictStatisticsType(
            total_idps=total_idps if total_idps else 0,
            new_displacements=conflict_qs.aggregate(
                total_new_displacement=Coalesce(models.Sum('new_displacement', output_field=models.IntegerField()), 0)
            )['total_new_displacement'],

            new_displacement_timeseries=[GiddTimeSeriesStatisticsType(**item) for item in new_displacement_timeseries_qs],
            idps_timeseries=[GiddTimeSeriesStatisticsType(**item) for item in idps_timeseries_qs],
        )

    @staticmethod
    def resolve_gidd_disaster_statistics(parent, info, **kwargs):
        disaster_qs = DisasterStatisticsFilter(data=kwargs).qs
        timeseries_qs = disaster_qs.filter(new_displacement__gt=0).values('year').annotate(
            total=Coalesce(models.Sum('new_displacement', output_field=models.IntegerField()), 0)
        ).order_by('year').values('year', 'total', 'country_id', 'country_name', 'iso3')

        # FIXME should we filter out not labeld hazard type?
        categories_qs = disaster_qs.values('hazard_type').annotate(
            total=Coalesce(models.Sum('new_displacement', output_field=models.IntegerField()), 0),
            label=models.Case(
                models.When(hazard_sub_category=None, then=models.Value('Not labeled')),
                default=models.F('hazard_type_name'),
                output_field=models.CharField()
            )
        ).filter(total__gte=1).values('label', 'total')
        return GiddDisasterStatisticsType(
            new_displacements=disaster_qs.aggregate(
                total_new_displacement=Coalesce(models.Sum('new_displacement', output_field=models.IntegerField()), 0)
            )['total_new_displacement'],

            total_events=disaster_qs.filter(new_displacement__gt=0).values('event__name').annotate(
                events=models.Count('id')
            ).aggregate(total_events=Coalesce(models.Sum('events', output_field=models.IntegerField()), 0))['total_events'],

            timeseries=[GiddDisasterTimeSeriesStatisticsType(
                year=item['year'],
                total=item['total'],
                country=GiddDisasterCountryType(
                    id=item['country_id'],
                    iso3=item['iso3'],
                    country_name=item['country_name']
                )
            ) for item in timeseries_qs],

            categories=[GiddCategoryStatisticsType(**item) for item in categories_qs]
        )

    @staticmethod
    def resolve_gidd_hazard_sub_types(parent, info, **kwargs):
        return [
            GiddHazardSubType(
                id=hazard['hazard_sub_type__id'],
                name=hazard['hazard_sub_type__name'],

            ) for hazard in Disaster.objects.values(
                'hazard_sub_type__id', 'hazard_sub_type__name'
            ).distinct(
                'hazard_sub_type__id', 'hazard_sub_type__name'
            )
        ]

    @staticmethod
    def resolve_gidd_year(parent, info, **kwargs):
        gidd_meta_data = ReleaseMetadata.objects.last()
        if kwargs['release_environment'] == ReleaseMetadata.ReleaseEnvironment.STAGING.name:
            return GiddYearType(year=gidd_meta_data.staging_year)
        if kwargs['release_environment'] == ReleaseMetadata.ReleaseEnvironment.PRODUCTION.name:
            return GiddYearType(year=gidd_meta_data.production_year)
