from django_filters import rest_framework as df

from apps.entry.models import Entry, EntryReviewer
from utils.filters import StringListFilter


class EntryFilter(df.FilterSet):
    article_title_contains = df.CharFilter(field_name='article_title', lookup_expr='icontains')
    country = df.NumberFilter(field_name='event__countries', lookup_expr='in')
    countries = StringListFilter(method='filter_countries')

    class Meta:
        model = Entry
        fields = ['event', 'created_by', 'reviewers']

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(event__countries__in=value).distinct()


class EntryReviewerFilter(df.FilterSet):
    class Meta:
        model = EntryReviewer
        fields = ('entry', )

    @property
    def qs(self):
        queryset = super().qs
        if 'entry' not in self.data:
            return queryset.none()
        return queryset
