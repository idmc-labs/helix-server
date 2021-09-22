from django_filters import rest_framework as df
from apps.entry.models import (
    EntryReviewer,
    OSMName,
)
from utils.filters import StringListFilter


class OSMNameFilter(df.FilterSet):
    class Meta:
        model = OSMName
        fields = []


class EntryReviewerFilter(df.FilterSet):
    status_in = StringListFilter(method='filter_status_in')

    class Meta:
        model = EntryReviewer
        fields = ('entry',)

    def filter_status_in(self, queryset, name, value):
        if value:
            # map enum names to values
            return queryset.filter(status__in=[EntryReviewer.REVIEW_STATUS.get(each) for each in value])
        return queryset
