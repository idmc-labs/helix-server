import typing
import datetime
import graphene
import django_filters
from django.core.exceptions import ValidationError
from django.utils.translation import gettext
from django.db import models
from django.http import HttpRequest

from utils.filters import SimpleInputFilter, generate_type_for_filter_set
from apps.report.models import Report
from apps.entry.models import Figure
from apps.country.models import Country
from apps.crisis.models import Crisis
from apps.event.models import Event
from apps.extraction.filters import (
    FigureExtractionNonAnnotateFilterSet,
    FigureExtractionFilterDataInputType,
    FigureExtractionFilterDataType,
)


class FigureFilterHelper:
    @staticmethod
    def get_report_id_from_filter_data(aggregate_figures_filter: typing.Optional[dict]) -> typing.Optional[int]:
        return (
            (
                aggregate_figures_filter or {}
            ).get('filter_figures') or {}
        ).get('report_id')

    @staticmethod
    def get_report(report_id: int) -> Report:
        report = Report.objects.filter(id=report_id).first()
        if report is None:
            raise ValidationError(gettext('Provided Report does not exist'))
        return report

    @staticmethod
    def filter_using_figure_filters(qs: models.QuerySet, filters: dict, request: HttpRequest) -> models.QuerySet:
        if not filters:
            return qs
        # XXX: Use this instead ReportFigureExtractionFilterSet?
        figure_qs = FigureExtractionNonAnnotateFilterSet(data=filters, request=request).qs
        figure_qs = Figure.objects.filter(
            id__in=figure_qs.values('id')
        )
        outer_ref_field = None
        if isinstance(qs.model, Country):
            outer_ref_field = 'country'
        elif isinstance(qs.model, Event):
            outer_ref_field = 'event'
        elif isinstance(qs.model, Crisis):
            outer_ref_field = 'event__crisis'

        if outer_ref_field is None:
            raise Exception(f'Unknown model used for `by figure filter`. {type(qs.model)}')

        return qs.filter(
            id__in=figure_qs.values(outer_ref_field)
        )

    @classmethod
    def aggregate_data_generate(
        cls,
        aggregate_figures_filter: typing.Optional[dict],
        request: HttpRequest,
    ) -> typing.Tuple[
        typing.Optional[models.QuerySet],
        typing.Optional[datetime.datetime],
    ]:
        report_id = cls.get_report_id_from_filter_data(aggregate_figures_filter)
        report = report_id and cls.get_report(report_id)
        if report:
            figure_qs = Figure.objects.filter(id__in=report.report_figures.values('id'))
            reference_date = report.filter_figure_end_before

        figure_filters = (aggregate_figures_filter or {}).get('filter_figures') or {}
        figure_qs = None
        reference_date = None

        if figure_filters:
            figure_qs = Figure.objects.filter(
                # XXX: Use this instead ReportFigureExtractionFilterSet?
                id__in=FigureExtractionNonAnnotateFilterSet(
                    data=figure_filters,
                    request=request,
                ).qs.values('id')
            )

        return figure_qs, reference_date


# -- Filters
class FigureAggregateFilter(django_filters.FilterSet):
    filter_figures = SimpleInputFilter(FigureExtractionFilterDataInputType, method='noop')

    def noop(self, qs, *_):
        return qs


class CountryFigureAggregateFilter(FigureAggregateFilter):
    year = django_filters.NumberFilter(method='noop')


FigureAggregateFilterDataType, FigureAggregateFilterDataInputType = generate_type_for_filter_set(
    FigureAggregateFilter,
    'entry.schema.figure_list',
    'FigureAggregateFilterDataType',
    'FigureAggregateFilterDataInputType',
    custom_new_fields_map={
        'filter_figures': graphene.Field(FigureExtractionFilterDataType),
    },
)

CountryFigureAggregateFilterDataType, CountryFigureAggregateFilterDataInputType = generate_type_for_filter_set(
    CountryFigureAggregateFilter,
    'entry.schema.figure_list',
    'CountryFigureAggregateFilterDataType',
    'CountryFigureAggregateFilterDataInputType',
    custom_new_fields_map={
        'filter_figures': graphene.Field(FigureExtractionFilterDataType),
    },
)
