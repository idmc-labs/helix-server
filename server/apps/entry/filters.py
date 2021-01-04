from django_filters import rest_framework as df

from apps.entry.models import Entry, EntryReviewer, OSMName
from utils.filters import StringListFilter


class OSMNameFilter(df.FilterSet):
    class Meta:
        model = OSMName
        fields = []


class EntryFilter(df.FilterSet):
    article_title_contains = df.CharFilter(field_name='article_title', lookup_expr='icontains')
    countries = StringListFilter(method='filter_countries')

    class Meta:
        model = Entry
        fields = ['event', 'created_by', 'reviewers']

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(event__countries__in=value).distinct()


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
