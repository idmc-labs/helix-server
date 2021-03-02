from django_filters import rest_framework as df

from apps.entry.models import Entry, Figure
from apps.crisis.models import Crisis
from utils.filters import StringListFilter, IDListFilter


class EntryExtractionFilterSet(df.FilterSet):
    # NOTE: these filter names exactly match the extraction query model field names
    event_regions = IDListFilter(method='filter_regions')
    event_countries = IDListFilter(method='filter_countries')
    event_crises = IDListFilter(method='filter_crises')
    figure_categories = IDListFilter(method='filter_figure_categories')
    figure_start_after = df.DateFilter(method='filter_time_frame_after')
    figure_end_before = df.DateFilter(method='filter_time_frame_before')
    figure_roles = StringListFilter(method='filter_figure_roles')
    entry_tags = IDListFilter(method='filter_tags')
    # TODO: GRID filter
    entry_article_title = df.CharFilter(field_name='article_title', lookup_expr='icontains')
    event_crisis_types = StringListFilter(method='filter_crisis_types')

    class Meta:
        model = Entry
        fields = {}

    def filter_regions(self, qs, name, value):
        if value:
            qs = qs.filter(figures__country__region__in=value).distinct()
        return qs

    def filter_countries(self, qs, name, value):
        if value:
            return qs.filter(figures__country__in=value).distinct()
        return qs

    def filter_crises(self, qs, name, value):
        if value:
            return qs.filter(event__crisis__in=value).distinct()
        return qs

    def filter_figure_categories(self, qs, name, value):
        if value:
            return qs.filter(figures__category__in=value).distinct()
        return qs

    def filter_time_frame_after(self, qs, name, value):
        if value:
            return qs.exclude(figures__start_date__isnull=True)\
                .filter(figures__start_date__gte=value).distinct()
        return qs

    def filter_time_frame_before(self, qs, name, value):
        if value:
            return qs.exclude(figures__end_date__isnull=True).\
                filter(figures__end_date__lt=value).distinct()
        return qs

    def filter_figure_roles(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(figures__role__in=value).distinct()
            else:
                # coming from client side
                return qs.filter(figures__role__in=[Figure.ROLE.get(item).value for item in
                                                    value]).distinct()
        return qs

    def filter_tags(self, qs, name, value):
        if value:
            return qs.filter(tags__in=value).distinct()
        return qs

    def filter_crisis_types(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(event__event_type__in=value).distinct()
            else:
                # coming from client side
                return qs.filter(event__event_type__in=[
                    Crisis.CRISIS_TYPE.get(item).value for item in value
                ])
        return qs


class FigureExtractionFilterSet(df.FilterSet):
    # NOTE: these filter names exactly match the extraction query model field names
    event_regions = IDListFilter(method='filter_regions')
    event_countries = IDListFilter(method='filter_countries')
    event_crises = IDListFilter(method='filter_crises')
    figure_categories = IDListFilter(method='filter_figure_categories')
    figure_start_after = df.DateFilter(method='filter_time_frame_after')
    # figure end before is applied with start after
    figure_roles = StringListFilter(method='filter_figure_roles')
    entry_tags = IDListFilter(method='filter_tags')
    # TODO: GRID filter
    entry_article_title = df.CharFilter(field_name='article_title', lookup_expr='icontains')
    event_crisis_types = StringListFilter(method='filter_crisis_types')

    class Meta:
        model = Figure
        fields = {}

    def filter_regions(self, qs, name, value):
        if value:
            qs = qs.filter(country__region__in=value).distinct()
        return qs

    def filter_countries(self, qs, name, value):
        if value:
            return qs.filter(country__in=value).distinct()
        return qs

    def filter_crises(self, qs, name, value):
        if value:
            return qs.filter(entry__event__crisis__in=value).distinct()
        return qs

    def filter_figure_categories(self, qs, name, value):
        if value:
            return qs.filter(category__in=value).distinct()
        return qs

    def filter_time_frame_after(self, qs, name, value):
        # NOTE: we are only checking if figure start time is between reporting dates
        if value:
            qs = qs.exclude(start_date__isnull=True)\
                .filter(start_date__gte=value)
            if 'figure_end_before' in self.data:
                qs = qs.filter(start_date__lt=self.data['figure_end_before'])
        return qs.distinct()

    def filter_figure_roles(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(role__in=value).distinct()
            else:
                # coming from client side
                return qs.filter(
                    role__in=[Figure.ROLE.get(item).value for item in value]
                ).distinct()
        return qs

    def filter_tags(self, qs, name, value):
        if value:
            return qs.filter(entry__tags__in=value).distinct()
        return qs

    def filter_crisis_types(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(entry__event__event_type__in=value).distinct()
            else:
                # coming from client side
                return qs.filter(entry__event__event_type__in=[
                    Crisis.CRISIS_TYPE.get(item).value for item in value
                ])
        return qs
