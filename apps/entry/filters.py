from django_filters import rest_framework as df
from apps.entry.models import (
    OSMName,
    DisaggregatedAge,
    Figure,
    FigureTag,
)


class OSMNameFilter(df.FilterSet):
    class Meta:
        model = OSMName
        fields = ['country']


class DisaggregatedAgeFilter(df.FilterSet):
    class Meta:
        model = DisaggregatedAge
        fields = {
            'sex': ['in'],
        }


class FigureFilter(df.FilterSet):
    class Meta:
        model = Figure
        fields = {
            'unit': ('exact',),
            'start_date': ('lte', 'gte'),
        }


class FigureTagFilter(df.FilterSet):
    class Meta:
        model = FigureTag
        fields = {
            'name': ('unaccent__icontains',),
        }
