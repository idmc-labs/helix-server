from django_filters import rest_framework as df

from apps.entry.models import Entry, Figure
from apps.extraction.models import ExtractionQuery
from apps.crisis.models import Crisis
from utils.filters import StringListFilter, IDListFilter


class EntryExtractionFilterSet(df.FilterSet):
    # NOTE: these filter names exactly match the extraction query model field names
    filter_figure_regions = IDListFilter(method='filter_regions')
    filter_figure_geographical_groups = IDListFilter(method='filter_geographical_groups')
    filter_figure_countries = IDListFilter(method='filter_countries')
    filter_event_crises = IDListFilter(method='filter_crises')
    filter_figure_categories = IDListFilter(method='filter_filter_figure_categories')
    filter_figure_start_after = df.DateFilter(method='filter_time_frame_after')
    filter_figure_end_before = df.DateFilter(method='filter_time_frame_before')
    filter_figure_roles = StringListFilter(method='filter_filter_figure_roles')
    filter_entry_tags = IDListFilter(method='filter_tags')
    # TODO: GRID filter
    filter_entry_article_title = df.CharFilter(field_name='article_title', lookup_expr='icontains')
    filter_event_crisis_types = StringListFilter(method='filter_crisis_types')

    class Meta:
        model = Entry
        fields = {}

    def filter_geographical_groups(self, qs, name, value):
        if value:
            qs = qs.filter(figures__country__geographical_group__in=value).distinct()
        return qs

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

    def filter_filter_figure_categories(self, qs, name, value):
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

    def filter_filter_figure_roles(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(figures__role__in=value).distinct()
            return qs.filter(figures__role__in=[
                Figure.ROLE.get(item).value for item in value
            ]).distinct()
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
            # coming from client side
            return qs.filter(event__event_type__in=[
                Crisis.CRISIS_TYPE.get(item).value for item in value
            ])
        return qs


class FigureExtractionFilterSet(df.FilterSet):
    # NOTE: these filter names exactly match the extraction query model field names
    filter_figure_regions = IDListFilter(method='filter_regions')
    filter_figure_geographical_groups = IDListFilter(method='filter_geographical_groups')
    filter_figure_countries = IDListFilter(method='filter_countries')
    filter_event_crises = IDListFilter(method='filter_crises')
    filter_figure_categories = IDListFilter(method='filter_filter_figure_categories')
    filter_figure_start_after = df.DateFilter(method='noop')
    filter_figure_end_before = df.DateFilter(method='noop')
    filter_figure_roles = StringListFilter(method='filter_filter_figure_roles')
    filter_entry_tags = IDListFilter(method='filter_tags')
    filter_entry_article_title = df.CharFilter(field_name='article_title', lookup_expr='icontains')
    filter_event_crisis_types = StringListFilter(method='filter_crisis_types')
    # NOTE: report filter is an exclusive filter
    report = df.CharFilter()

    class Meta:
        model = Figure
        fields = ['entry']

    def noop(self, qs, *args):
        return qs

    def filter_geographical_groups(self, qs, name, value):
        if value:
            qs = qs.filter(country__geographical_group__in=value).distinct()
        return qs

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

    def filter_filter_figure_categories(self, qs, name, value):
        if value:
            return qs.filter(category__in=value).distinct()
        return qs

    def filter_filter_figure_roles(self, qs, name, value):
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

    @property
    def qs(self):
        from apps.report.models import Report

        # if report is in the filter params, will ignore everything else
        if 'report' in self.data:
            report = Report.objects.get(id=self.data['report'])
            return report.report_figures
        queryset = super().qs
        start_date = self.data.get('filter_figure_start_after')
        end_date = self.data.get('filter_figure_end_before')

        flow_qs = Figure.filtered_nd_figures(
            queryset, start_date, end_date
        )
        stock_qs = Figure.filtered_idp_figures(
            queryset, end_date
        )
        return flow_qs | stock_qs


class ExtractionQueryFilter(df.FilterSet):
    class Meta:
        model = ExtractionQuery
        fields = {
            'id': ('exact',),
            'name': ('icontains',),
        }

    @property
    def qs(self):
        if self.request.user.is_authenticated:
            return super().qs.filter(created_by=self.request.user)
        return ExtractionQuery.objects.none()
