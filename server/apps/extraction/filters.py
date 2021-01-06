from django_filters import rest_framework as df

from apps.entry.models import Entry
from utils.filters import StringListFilter


class EntryExtractionFilterSet(df.FilterSet):
    # NOTE: these filter names exactly match the extraction query model field names
    regions = StringListFilter(method='filter_regions')
    countries = StringListFilter(method='filter_countries')
    districts = StringListFilter(method='filter_districts')
    crises = StringListFilter(method='filter_crises')
    figure_categories = StringListFilter(method='filter_figure_categories')
    event_after = df.DateFilter(method='filter_time_frame_after')
    event_before = df.DateFilter(method='filter_time_frame_before')
    figure_roles = StringListFilter(method='filter_figure_roles')
    figure_tags = StringListFilter(method='filter_figure_tags')
    # TODO: GRID filter

    class Meta:
        model = Entry
        fields = []

    def filter_regions(self, qs, name, value):
        if not value:
            return qs
        qs = qs.filter(event__countries__region__in=value).distinct()
        return qs

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(event__countries__in=value).distinct()

    def filter_districts(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(figures__disctrict__in=value).distinct()

    def filter_crises(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(event__crisis__in=value).distinct()

    def filter_figure_categories(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(figures__category__in=value).distinct()

    def filter_time_frame_after(self, qs, name, value):
        if not value:
            return qs
        return qs.exclude(figures__start_date__isnull=True)\
            .filter(figures__start_date__gte=value).distinct()

    def filter_time_frame_before(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(figures__end_date__lt=value).distinct()

    def filter_figure_roles(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(figures__role__in=value).distinct()

    def filter_figure_tags(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(tags__in=value).distinct()
