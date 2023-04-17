import strawberry
from typing import List, Optional
from django.db.models.functions import Coalesce
from .types import (
    ConflictType,
    DisasterType,
    CountryType,
    ConflictListType,
    DisasterListType,
    CountryListType,
    DisasterStatisticsType,
    TimeSeriesStatisticsType,
    DisasterTimeSeriesStatisticsType,
    CategoryStatisticsType,
    ConflictStatisticsType,
    DisasterCountryType,
)
from .models import Disaster, Conflict
from django.db.models import Value, Sum, F, Count, CharField, Case, When, IntegerField
from .gh_filters import DisasterStatisticsFilter, ConflictStatisticsFilter
from strawberry_django.filters import apply as filter_apply
from asgiref.sync import sync_to_async
from apps.country.models import Country


@sync_to_async
def disaster_statistics_qs(disaster_qs) -> DisasterStatisticsType:
    timeseries_qs = disaster_qs.filter(new_displacement__gt=0).values('year').annotate(
        total=Coalesce(Sum('new_displacement', output_field=IntegerField()), 0)
    ).order_by('year').values('year', 'total')

    # FIXME should we filter out not labeld hazard type?
    categories_qs = disaster_qs.filter(hazard_type__isnull=False).values('hazard_type').annotate(
        total=Coalesce(Sum('new_displacement', output_field=IntegerField()), 0),
        label=Case(
            When(hazard_sub_category=None, then=Value('Not labeled')),
            default=F('hazard_type'),
            output_field=CharField()
        )
    ).filter(total__gte=1).values('label', 'total')
    return DisasterStatisticsType(
        new_displacements=disaster_qs.aggregate(
            total_new_displacement=Coalesce(Sum('new_displacement', output_field=IntegerField()), 0)
        )['total_new_displacement'],

        total_events=disaster_qs.filter(new_displacement__gt=0).values('event__name').annotate(
            events=Count('id')
        ).aggregate(total_events=Coalesce(Sum('events', output_field=IntegerField()), 0))['total_events'],

        timeseries=[DisasterTimeSeriesStatisticsType(
            year=item['year'],
            total=item['total'],
        ) for item in timeseries_qs],

        categories=[CategoryStatisticsType(**item) for item in categories_qs]
    )


@sync_to_async
def conflict_statistics_qs(conflict_qs) -> ConflictStatisticsType:
    new_displacement_timeseries_qs = conflict_qs.filter(
        new_displacement__gt=0
    ).values('year').annotate(
        total=Sum('new_displacement', output_field=IntegerField()),
    ).order_by('year').values('year', 'total')

    idps_timeseries_qs = conflict_qs.filter(
        total_displacement__isnull=False
    ).values('year').annotate(
        total=Sum('total_displacement', output_field=IntegerField())
    ).order_by('year').values('year', 'total')
    total_idps = conflict_qs.order_by('-year').first().total_displacement if conflict_qs.order_by('-year') else 0
    return ConflictStatisticsType(
        total_idps=total_idps if total_idps else 0,
        new_displacements=conflict_qs.aggregate(
            total_new_displacement=Coalesce(Sum('new_displacement', output_field=IntegerField()), 0)
        )['total_new_displacement'],

        new_displacement_timeseries=[TimeSeriesStatisticsType(**item) for item in new_displacement_timeseries_qs],
        idps_timeseries=[TimeSeriesStatisticsType(**item) for item in idps_timeseries_qs],
    )


@sync_to_async
def get_country_object(pk, iso3):
    if pk:
        return Country.objects.get(pk=pk)
    if iso3:
        return Country.objects.get(iso3=iso3)


@strawberry.type
class Query:
    conflicts: List[ConflictListType] = strawberry.django.field()
    disasters: List[DisasterListType] = strawberry.django.field()
    countries: List[CountryListType] = strawberry.django.field()
    conflict: ConflictType = strawberry.django.field()
    disaster: DisasterType = strawberry.django.field()

    @strawberry.field
    def country(self, pk: Optional[strawberry.ID] = None, iso3: Optional[str] = None) -> CountryType:
        return get_country_object(pk, iso3)

    @strawberry.field
    def disaster_statistics(self, filters: DisasterStatisticsFilter) -> DisasterStatisticsType:
        return disaster_statistics_qs(filter_apply(filters, Disaster.objects.all()))

    @strawberry.field
    def conflict_statistics(self, filters: ConflictStatisticsFilter) -> ConflictStatisticsType:
        return conflict_statistics_qs(filter_apply(filters, Conflict.objects.all()))

