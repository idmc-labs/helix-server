from django_filters import rest_framework as df
from apps.entry.models import (
    OSMName,
)


class OSMNameFilter(df.FilterSet):
    class Meta:
        model = OSMName
        fields = []
