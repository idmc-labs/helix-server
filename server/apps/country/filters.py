import django_filters
from django.db.models import Value
from django.db.models.functions import Lower, StrIndex

from apps.country.models import Country
from utils.filters import StringListFilter


class CountryFilter(django_filters.FilterSet):
    country_name = django_filters.CharFilter(method='filter_country_name')
    regions = StringListFilter(method='filter_regions')

    class Meta:
        model = Country
        fields = []

    def filter_country_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.annotate(
            lname=Lower('name')
        ).annotate(
            idx=StrIndex('lname', Value(value.lower()))
        ).filter(idx__gt=0).order_by('idx', 'name')

    def filter_regions(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(region__in=value).distinct()
