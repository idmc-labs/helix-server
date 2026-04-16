import graphene
from django.db.models import Count
from django.http import HttpRequest

from apps.crisis.models import Crisis
from apps.extraction.filters import (
    FigureExtractionFilterDataInputType,
    FigureExtractionFilterDataType,
)
from utils.figure_filter import (
    FigureAggregateFilterDataInputType,
    FigureAggregateFilterDataType,
    FigureFilterHelper,
)
from utils.filters import (
    IDListFilter,
    MultiWordSearchFilterSet,
    SimpleInputFilter,
    StringListFilter,
    generate_type_for_filter_set,
)


class CrisisFilter(MultiWordSearchFilterSet):
    countries = IDListFilter(method="filter_countries")
    crisis_types = StringListFilter(method="filter_crisis_types")
    events = IDListFilter(method="filter_events")

    filter_figures = SimpleInputFilter(FigureExtractionFilterDataInputType, method="filter_by_figures")
    aggregate_figures = SimpleInputFilter(FigureAggregateFilterDataInputType, method="noop")

    # used in report crisis table
    created_by_ids = IDListFilter(method="filter_created_by")

    request: HttpRequest

    class Meta:
        model = Crisis
        fields = {
            "created_at": ["lt", "lte", "gt", "gte"],
            "start_date": ["lt", "lte", "gt", "gte"],
            "end_date": ["lt", "lte", "gt", "gte"],
        }
        multi_word_search_fields = ["name", "events__name"]

    def noop(self, qs, name, value):
        return qs

    def filter_by_figures(self, qs, _, value):
        return FigureFilterHelper.filter_using_figure_filters(qs, value, self.request)

    def filter_events(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(events__in=value).distinct()

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(countries__in=value).distinct()

    def filter_crisis_types(self, qs, name, value):
        if not value:
            return qs
        if isinstance(value[0], int):
            # internal filtering
            return qs.filter(crisis_type__in=value).distinct()
        # client side filtering
        return qs.filter(crisis_type__in=[Crisis.CRISIS_TYPE.get(item).value for item in value]).distinct()

    def filter_created_by(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(created_by__in=value)

    @property
    def qs(self):
        figure_qs, reference_date = FigureFilterHelper.aggregate_data_generate(
            self.data.get("aggregate_figures"),
            self.request,
        )
        return (
            super()
            .qs.annotate(
                **Crisis._total_figure_disaggregation_subquery(
                    figures=figure_qs,
                    reference_date=reference_date,
                ),
                **Crisis.annotate_review_figures_count(),
                event_count=Count("events"),
            )
            .prefetch_related("events")
            .distinct()
        )


CrisisFilterDataType, CrisisFilterDataInputType = generate_type_for_filter_set(
    CrisisFilter,
    "crisis.schema.crisis_list",
    "CrisisFilterDataType",
    "CrisisFilterDataInputType",
    custom_new_fields_map={
        "filter_figures": graphene.Field(FigureExtractionFilterDataType),
        "aggregate_figures": graphene.Field(FigureAggregateFilterDataType),
    },
)
