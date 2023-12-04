import graphene
import django_filters
from datetime import datetime
from django.utils import timezone
from django.db.models import (
    Value,
)
from django.db.models.functions import Lower, StrIndex
from django.utils.translation import gettext
from django.core.exceptions import ValidationError

from apps.country.models import (
    Country,
    CountryRegion,
    GeographicalGroup,
    MonitoringSubRegion,
    ContextualAnalysis,
    Summary,
)
from apps.report.models import Report
from apps.extraction.filters import (
    FigureExtractionFilterSet,
    FigureExtractionFilterDataInputType,
    FigureExtractionFilterDataType,
)
from utils.filters import (
    IDListFilter,
    StringListFilter,
    NameFilterMixin,
    SimpleInputFilter,
    generate_type_for_filter_set,
)


class GeographicalGroupFilter(NameFilterMixin,
                              django_filters.FilterSet):
    name = django_filters.CharFilter(method='_filter_name')

    class Meta:
        model = GeographicalGroup
        fields = {
            'id': ['iexact'],
        }


class CountryRegionFilter(NameFilterMixin,
                          django_filters.FilterSet):
    name = django_filters.CharFilter(method='_filter_name')

    class Meta:
        model = CountryRegion
        fields = {
            'id': ['iexact'],
        }


class CountryFilter(django_filters.FilterSet):
    country_name = django_filters.CharFilter(method='_filter_name')
    region_name = django_filters.CharFilter(method='filter_region_name')
    geographical_group_name = django_filters.CharFilter(method='filter_geo_group_name')
    region_by_ids = StringListFilter(method='filter_regions')
    geo_group_by_ids = StringListFilter(method='filter_geo_groups')

    filter_figures = SimpleInputFilter(FigureExtractionFilterDataInputType, method='noop')

    # used in report country table
    report_id = django_filters.CharFilter(method='noop')
    year = django_filters.NumberFilter(method='filter_year')
    events = IDListFilter(method='filter_by_events')
    crises = IDListFilter(method='filter_by_crisis')

    class Meta:
        model = Country
        fields = {
            'iso3': ['unaccent__icontains'],
            'id': ['iexact'],
        }

    def noop(self, qs, name, value):
        return qs

    def filter_by_events(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(
            id__in=Country.objects.filter(events__in=value).values('id')
        )

    def filter_by_crisis(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(
            id__in=Country.objects.filter(crises__in=value).values('id')
        )

    def _filter_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.annotate(
            lname=Lower('idmc_short_name')
        ).annotate(
            idx=StrIndex('lname', Value(value.lower()))
        ).filter(idx__gt=0).order_by('idx', 'idmc_short_name')

    def filter_geo_group_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.select_related(
            'geographical_group'
        ).annotate(
            geo_name=Lower('geographical_group__name')
        ).annotate(
            idx=StrIndex('geo_name', Value(value.lower()))
        ).filter(idx__gt=0).order_by('idx', 'geo_name')

    def filter_region_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.select_related(
            'region'
        ).annotate(
            region_name=Lower('region__name')
        ).annotate(
            idx=StrIndex('region_name', Value(value.lower()))
        ).filter(idx__gt=0).order_by('idx', 'region_name')

    def filter_regions(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(region__in=value).distinct()

    def filter_geo_groups(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(geographical_group__in=value).distinct()

    def filter_year(self, qs, name, value):
        ''' Filter logic is applied in qs'''
        return qs

    @property
    def qs(self):
        report_id = self.data.get('report_id')
        year = self.data.get('year')
        report = report_id and Report.objects.filter(id=report_id).first()
        if report_id is not None and report is None:
            raise ValidationError(gettext('Provided Report doesnot exists'))
        # Only 1 is allowed among report and year
        if report and year:
            raise ValidationError(gettext('Cannot pass both report and year in filter'))

        figure_qs = None
        start_date = None
        end_date = None
        if report:
            figure_qs = report.report_figures
            end_date = report.filter_figure_end_before
        else:
            year = year or timezone.now().year
            start_date = datetime(year=int(year), month=1, day=1)
            end_date = datetime(year=int(year), month=12, day=31)

        filter_figures_data = self.data.get('filter_figures')
        if filter_figures_data:
            figure_qs = FigureExtractionFilterSet(
                data=filter_figures_data,
                request=self.request,
                queryset=figure_qs,
            ).qs

        qs = super().qs
        if figure_qs is not None:
            qs = qs.filter(id__in=figure_qs.values('country'))

        qs = qs.annotate(
            **Country._total_figure_disaggregation_subquery(
                figures=figure_qs,
                start_date=start_date,
                end_date=end_date,
            )
        )
        return qs


class MonitoringSubRegionFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(method='_filter_name')

    class Meta:
        model = MonitoringSubRegion
        fields = ['id']

    def _filter_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.annotate(
            lname=Lower('name')
        ).annotate(
            idx=StrIndex('lname', Value(value.lower()))
        ).filter(idx__gt=0).order_by('idx', 'name')


class CountrySummaryFilter(django_filters.FilterSet):
    class Meta:
        model = Summary
        fields = {
            'created_at': ['lte', 'gte']
        }


class ContextualAnalysisFilter(django_filters.FilterSet):
    class Meta:
        model = ContextualAnalysis
        fields = {
            'created_at': ['lte', 'gte']
        }


CountryFilterDataType, CountryFilterDataInputType = generate_type_for_filter_set(
    CountryFilter,
    'entry.schema.figure_list',
    'CountryFilterDataType',
    'CountryFilterDataInputType',
    custom_new_fields_map={
        'filter_figures': graphene.Field(FigureExtractionFilterDataType),
    },
)
