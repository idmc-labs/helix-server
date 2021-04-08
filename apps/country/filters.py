import django_filters
from django.db.models import (
    Value,
)
from django.db.models.functions import Lower, StrIndex

from apps.country.models import (
    Country,
    CountryRegion,
    GeographicalGroup,
)
from utils.filters import StringListFilter


class NameFilterMixin:
    name = django_filters.CharFilter(method='_filter_name')

    def _filter_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.annotate(
            lname=Lower('name')
        ).annotate(
            idx=StrIndex('lname', Value(value.lower()))
        ).filter(idx__gt=0).order_by('idx', 'name')


class GeographicalGroupFilter(NameFilterMixin,
                              django_filters.FilterSet):
    class Meta:
        model = GeographicalGroup
        fields = {
            'id': ['iexact'],
        }


class CountryRegionFilter(NameFilterMixin,
                          django_filters.FilterSet):
    class Meta:
        model = CountryRegion
        fields = {
            'id': ['iexact'],
        }


class CountryFilter(NameFilterMixin,
                    django_filters.FilterSet):
    region_name = django_filters.CharFilter(method='filter_region_name')
    geographical_group_name = django_filters.CharFilter(method='filter_geo_group_name')
    region_by_ids = StringListFilter(method='filter_regions')

    class Meta:
        model = Country
        fields = {
            'iso3': ['icontains'],
            'id': ['iexact'],
        }

    def filter_geo_group_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.select_related(
            'geographical_group'
        ).annotate(
            geo_name=Lower('geographical_group__name')
        ).annotate(
            idx=StrIndex('geo_name', Value(value.lower()))
        ).filter(idx__gt=0).order_by('idx', 'geo_name')

    def filter_region_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.select_related(
            'region'
        ).annotate(
            region_name=Lower('region__name')
        ).annotate(
            idx=StrIndex('region_name', Value(value.lower()))
        ).filter(idx__gt=0).order_by('idx', 'region_name')

    def filter_regions(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(region__in=value).distinct()
