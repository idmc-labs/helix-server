# types.py
import graphene
from graphene_django_extras import DjangoObjectField
from graphene_django.filter.utils import get_filtering_args_from_filterset
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.pagination import PageGraphqlPaginationWithoutCount
from utils.graphene.enums import EnumDescription

from django.db import models
from django.db.models.functions import Coalesce
from .models import (
    Conflict,
    Disaster,
    StatusLog,
    ReleaseMetadata,
)
from graphene_django import DjangoObjectType
from .gh_filters import (
    ConflictFilter,
    DisasterFilter,
    ConflictStatisticsFilter,
    DisasterStatisticsFilter,
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


class GiddReleaseMetadataType(DjangoObjectType):
    class Meta:
        model = ReleaseMetadata


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

    @staticmethod
    def resolve_gidd_release_meta_data(parent, info, **kwargs):
        return ReleaseMetadata.objects.first()

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
