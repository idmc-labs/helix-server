from django_filters import rest_framework as df
from django.db import models

from apps.crisis.models import Crisis
from apps.extraction.models import ExtractionQuery
from apps.entry.models import (
    Entry,
    Figure,
    EntryReviewer,
    FigureDisaggregationAbstractModel,
)
from utils.filters import StringListFilter, IDListFilter

RURAL = FigureDisaggregationAbstractModel.DISPLACEMENT_TYPE.RURAL.name
URBAN = FigureDisaggregationAbstractModel.DISPLACEMENT_TYPE.URBAN.name
MALE = FigureDisaggregationAbstractModel.GENDER_TYPE.MALE.name
FEMALE = FigureDisaggregationAbstractModel.GENDER_TYPE.FEMALE.name


class EntryExtractionFilterSet(df.FilterSet):
    # NOTE: these filter names exactly match the extraction query model field names
    filter_figure_regions = IDListFilter(method='filter_regions')
    filter_figure_geographical_groups = IDListFilter(method='filter_geographical_groups')
    filter_figure_countries = IDListFilter(method='filter_countries')
    filter_events = IDListFilter(method='filter_events_')
    filter_event_crises = IDListFilter(method='filter_crises')
    filter_entry_sources = IDListFilter(method='filter_sources')
    filter_entry_publishers = IDListFilter(method='filter_publishers')
    filter_figure_categories = IDListFilter(method='filter_filter_figure_categories')
    filter_figure_category_types = StringListFilter(method='filter_filter_figure_category_types')
    filter_figure_start_after = df.DateFilter(method='filter_time_frame_after')
    filter_figure_end_before = df.DateFilter(method='filter_time_frame_before')
    filter_figure_roles = StringListFilter(method='filter_filter_figure_roles')
    filter_entry_tags = IDListFilter(method='filter_tags')
    filter_entry_article_title = df.CharFilter(field_name='article_title', lookup_expr='icontains')
    filter_event_glide_number = df.CharFilter(field_name='event__glide_number', lookup_expr='icontains')
    filter_event_crisis_types = StringListFilter(method='filter_crisis_types')
    filter_entry_review_status = StringListFilter(method='filter_by_review_status')
    filter_entry_created_by = IDListFilter(field_name='created_by', lookup_expr='in')
    filter_figure_displacement_types = StringListFilter(method='filter_by_figure_displacement_types')
    filter_figure_sex_types = StringListFilter(method='filter_by_figure_sex_types')

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

    def filter_events_(self, qs, name, value):
        if value:
            return qs.filter(event__in=value).distinct()
        return qs

    def filter_crises(self, qs, name, value):
        if value:
            return qs.filter(event__crisis__in=value).distinct()
        return qs

    def filter_sources(self, qs, name, value):
        if value:
            return qs.filter(sources__in=value).distinct()
        return qs

    def filter_publishers(self, qs, name, value):
        if value:
            return qs.filter(publishers__in=value).distinct()
        return qs

    def filter_filter_figure_categories(self, qs, name, value):
        if value:
            return qs.filter(figures__category__in=value).distinct()
        return qs

    def filter_filter_figure_category_types(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(figures__category__type__in=value).distinct()

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

    def filter_by_review_status(self, qs, name, value):
        if not value:
            return qs
        db_values = [EntryReviewer.REVIEW_STATUS.get(item) for item in value]
        return qs.filter(review_status__in=db_values)

    def filter_by_figure_sex_types(self, qs, name, value):
        if not value:
            return qs

        query_expr = models.Q()
        if MALE in value:
            query_expr = query_expr | models.Q(figures__disaggregation_sex_male__gt=0)
        if FEMALE in value:
            query_expr = query_expr | models.Q(figures__disaggregation_sex_female__gt=0)
        return qs.filter(query_expr).distinct()

    def filter_by_figure_displacement_types(self, qs, name, value):
        if not value:
            return qs

        query_expr = models.Q()
        if RURAL in value:
            query_expr = query_expr | models.Q(figures__disaggregation_displacement_rural__gt=0)
        if URBAN in value:
            query_expr = query_expr | models.Q(figures__disaggregation_displacement_urban__gt=0)
        return qs.filter(query_expr).distinct()


class FigureExtractionFilterSet(df.FilterSet):
    # NOTE: these filter names exactly match the extraction query model field names
    filter_figure_regions = IDListFilter(method='filter_regions')
    filter_figure_geographical_groups = IDListFilter(method='filter_geographical_groups')
    filter_figure_countries = IDListFilter(method='filter_countries')
    filter_events = IDListFilter(method='filter_events_')
    filter_event_crises = IDListFilter(method='filter_crises')
    filter_entry_sources = IDListFilter(method='filter_sources')
    filter_entry_publishers = IDListFilter(method='filter_publishers')
    filter_figure_categories = IDListFilter(method='filter_filter_figure_categories')
    filter_figure_category_types = StringListFilter(field_name='category__type', lookup_expr='in')
    filter_figure_start_after = df.DateFilter(method='noop')
    filter_figure_end_before = df.DateFilter(method='noop')
    filter_figure_roles = StringListFilter(method='filter_filter_figure_roles')
    filter_entry_tags = IDListFilter(method='filter_tags')
    filter_entry_article_title = df.CharFilter(field_name='entry__article_title', lookup_expr='icontains')
    filter_event_crisis_types = StringListFilter(method='filter_crisis_types')
    filter_event_glide_number = df.CharFilter(field_name='entry__event__glide_number', lookup_expr='icontains')
    filter_entry_review_status = StringListFilter(method='filter_by_review_status')
    filter_entry_created_by = IDListFilter(field_name='entry__created_by', lookup_expr='in')
    filter_figure_displacement_types = StringListFilter(method='filter_by_figure_displacement_types')
    filter_figure_sex_types = StringListFilter(method='filter_by_figure_sex_types')

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

    def filter_events_(self, qs, name, value):
        if value:
            return qs.filter(entry__event__in=value).distinct()
        return qs

    def filter_crises(self, qs, name, value):
        if value:
            return qs.filter(entry__event__crisis__in=value).distinct()
        return qs

    def filter_sources(self, qs, name, value):
        if value:
            return qs.filter(entry__sources__in=value).distinct()
        return qs

    def filter_publishers(self, qs, name, value):
        if value:
            return qs.filter(entry__publishers__in=value).distinct()
        return qs

    def filter_filter_figure_categories(self, qs, name, value):
        if value:
            return qs.filter(category__in=value).distinct()
        return qs

    def filter_filter_figure_category_types(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(category__type__in=value).distinct()

    def filter_filter_figure_roles(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(role__in=value)
            else:
                # coming from client side
                return qs.filter(
                    role__in=[Figure.ROLE.get(item).value for item in value]
                )
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

    def filter_by_review_status(self, qs, name, value):
        if not value:
            return qs
        db_values = [EntryReviewer.REVIEW_STATUS.get(item) for item in value]
        return qs.filter(entry__review_status__in=db_values)

    def filter_by_figure_sex_types(self, qs, name, value):
        if not value:
            return qs

        query_expr = models.Q()
        if MALE in value:
            query_expr = query_expr | models.Q(disaggregation_sex_male__gt=0)
        if FEMALE in value:
            query_expr = query_expr | models.Q(disaggregation_sex_female__gt=0)
        return qs.filter(query_expr)

    def filter_by_figure_displacement_types(self, qs, name, value):
        if not value:
            return qs

        query_expr = models.Q()
        if RURAL in value:
            query_expr = query_expr | models.Q(disaggregation_displacement_rural__gt=0)
        if URBAN in value:
            query_expr = query_expr | models.Q(disaggregation_displacement_urban__gt=0)
        return qs.filter(query_expr)

    @property
    def qs(self):
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
