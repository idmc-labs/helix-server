from django_filters import rest_framework as df

from apps.entry.models import (
    Entry,
    EntryReviewer,
    OSMName,
    Figure,
)
from utils.filters import StringListFilter


class OSMNameFilter(df.FilterSet):
    class Meta:
        model = OSMName
        fields = []


class FigureFilter(df.FilterSet):
    categories = StringListFilter(method='filter_figure_categories')
    start_date = df.DateFilter(method='filter_time_frame_after')
    end_date = df.DateFilter(method='filter_time_frame_before')
    roles = StringListFilter(method='filter_figure_roles')

    class Meta:
        model = Figure
        fields = []

    def filter_figure_categories(self, qs, name, value):
        if value:
            return qs.filter(category__in=value)
        return qs

    def filter_time_frame_after(self, qs, name, value):
        if value:
            return qs.exclude(start_date__isnull=True)\
                .filter(start_date__gte=value)
        return qs

    def filter_time_frame_before(self, qs, name, value):
        if value:
            return qs.exclude(end_date__isnull=True).\
                filter(end_date__lt=value)
        return qs

    def filter_figure_roles(self, qs, name, value):
        if value:
            return qs.filter(role__in=value)
        return qs


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
