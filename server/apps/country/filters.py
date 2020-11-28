import django_filters
from django.db.models import Value
from django.db.models.functions import Lower, StrIndex

from apps.country.models import Country


class CountryFilter(django_filters.FilterSet):
    country_name = django_filters.CharFilter(method='filter_country_name')

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
