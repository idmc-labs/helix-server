from django_filters import rest_framework as df

from apps.entry.models import (
    DisaggregatedAge,
    Figure,
    FigureLocation,
    FigureTag,
)


class FigureLocationFilter(df.FilterSet):
    class Meta:
        model = FigureLocation
        fields = ["country"]


class DisaggregatedAgeFilter(df.FilterSet):
    class Meta:
        model = DisaggregatedAge
        fields = {
            "sex": ["in"],
        }


class FigureFilter(df.FilterSet):
    class Meta:
        model = Figure
        fields = {
            "unit": ("exact",),
            "start_date": ("lte", "gte"),
        }


class FigureTagFilter(df.FilterSet):
    class Meta:
        model = FigureTag
        fields = {
            "name": ("unaccent__icontains",),
        }
