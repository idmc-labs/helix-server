from django.db.models import Exists, OuterRef
from django_filters import rest_framework as df

from apps.entry.models import (
    Entry,
    EntryReviewer,
    OSMName,
    Figure,
)
from utils.filters import StringListFilter, IDListFilter

under_review_subquery = EntryReviewer.objects.filter(
    entry=OuterRef('pk'),
    status=EntryReviewer.REVIEW_STATUS.UNDER_REVIEW
)
reviewed_subquery = EntryReviewer.objects.filter(
    entry=OuterRef('pk'),
    status=EntryReviewer.REVIEW_STATUS.REVIEW_COMPLETED
)
signed_off_subquery = EntryReviewer.objects.filter(
    entry=OuterRef('pk'),
    status=EntryReviewer.REVIEW_STATUS.SIGNED_OFF
)


class OSMNameFilter(df.FilterSet):
    class Meta:
        model = OSMName
        fields = []


class FigureFilter(df.FilterSet):
    categories = StringListFilter(method='filter_filter_figure_categories')
    start_date = df.DateFilter()
    end_date = df.DateFilter()
    roles = StringListFilter(method='filter_filter_figure_roles')
    entry = df.NumberFilter(field_name='entry', lookup_expr='exact')
    event = df.NumberFilter(field_name='entry__event', lookup_expr='exact')
    crisis = df.NumberFilter(field_name='entry__event__crisis', lookup_expr='exact')

    class Meta:
        model = Figure
        fields = []

    def filter_filter_figure_categories(self, qs, name, value):
        if value:
            return qs.filter(category__in=value)
        return qs

    def filter_filter_figure_roles(self, qs, name, value):
        if value:
            return qs.filter(role__in=[Figure.ROLE.get(item) for item in value]).distinct()
        return qs

    @property
    def qs(self):
        queryset = super().qs

        start_date = self.data.get('start_date')
        end_date = self.data.get('end_date')
        flow_qs = Figure.filtered_nd_figures(
            queryset, start_date, end_date
        )
        stock_qs = Figure.filtered_idp_figures(
            queryset, end_date
        )
        return flow_qs | stock_qs


class EntryFilter(df.FilterSet):
    article_title_contains = df.CharFilter(field_name='article_title', lookup_expr='icontains')
    countries = IDListFilter(method='filter_countries')
    sources_by_ids = IDListFilter(method='filter_sources')
    publishers_by_ids = IDListFilter(method='filter_publishers')
    created_by_ids = IDListFilter(method='filter_created_by')

    class Meta:
        model = Entry
        fields = {
            'event': ['exact'],
            'is_confidential': ['exact'],
            'publish_date': ['lt', 'lte', 'gt', 'gte'],
        }

    def filter_created_by(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(created_by__in=value)

    def filter_publishers(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(publishers__in=value).distinct()

    def filter_sources(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(sources__in=value).distinct()

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(event__countries__in=value)

    @property
    def qs(self):
        return super().qs.annotate(
            _is_reviewed=Exists(reviewed_subquery),
            _is_under_review=Exists(under_review_subquery),
            _is_signed_off=Exists(signed_off_subquery),
        ).distinct()


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
