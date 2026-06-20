import graphene
from django.db.models import Count, Exists, OuterRef
from django.http import HttpRequest

from apps.crisis.models import Crisis
from apps.event.models import Event
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
    # Opt-in: DjangoPaginatedListObjectField uses this marker to decide whether
    # to forward the active ordering as a constructor arg, so we can gate
    # expensive annotations on it (see qs property below).
    accepts_ordering = True

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

    def __init__(self, *args, ordering=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ordering = ordering
        self.ordering_fields = {field.lstrip("-") for field in ordering.split(",") if field} if ordering else set()

    def noop(self, qs, name, value):
        return qs

    def filter_by_figures(self, qs, _, value):
        return FigureFilterHelper.filter_using_figure_filters(qs, value, self.request)

    def filter_events(self, qs, name, value):
        if not value:
            return qs
        # reverse FK (one-to-many): Exists avoids one outer row per matching event,
        # so no .distinct() is needed.
        return qs.filter(Exists(Event.objects.filter(crisis_id=OuterRef("pk"), pk__in=value)))

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        # M2M: Exists membership test, no fan-out -> no .distinct().
        return qs.filter(Exists(Crisis.countries.through.objects.filter(crisis_id=OuterRef("pk"), country_id__in=value)))

    def filter_crisis_types(self, qs, name, value):
        if not value:
            return qs
        # crisis_type is a scalar field: no join, no fan-out, no .distinct().
        if isinstance(value[0], int):
            # internal filtering
            return qs.filter(crisis_type__in=value)
        # client side filtering
        return qs.filter(crisis_type__in=[Crisis.CRISIS_TYPE.get(item).value for item in value])

    def filter_created_by(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(created_by__in=value)

    @property
    def qs(self):
        queryset = super().qs

        figure_qs, reference_date = FigureFilterHelper.aggregate_data_generate(
            self.data.get("aggregate_figures"),
            self.request,
        )
        # The figure-disaggregation (nd/idp) annotations are only needed in the queryset
        # when either the client asked for a filtered aggregate (aggregate_figures) or the
        # list is ordered by one of them. Otherwise CrisisType resolvers fall back to the
        # (unfiltered) dataloaders, which return identical values without per-row subqueries
        # over every crisis. When aggregate_figures is provided the annotation reflects the
        # filtered aggregate, so it must stay regardless of ordering.
        figure_disaggregation = Crisis._total_figure_disaggregation_subquery(
            figures=figure_qs,
            reference_date=reference_date,
        )
        # has_figure_scope: aggregate_figures resolved to an actual figure set (a report or a
        # non-empty filter_figures) — not merely whether the field was passed. (reference_date is
        # only ever set alongside figure_qs, so checking figure_qs alone is enough.)
        has_figure_scope = figure_qs is not None
        if has_figure_scope or (self.ordering_fields & set(figure_disaggregation.keys())):
            queryset = queryset.annotate(**figure_disaggregation)

        # The review-figure counts are an expensive fan-out aggregation over the whole
        # Figure table (Count over a crisis->event->figure join + GroupAggregate). They are
        # only needed in the queryset when the list is ordered by one of them; otherwise the
        # review_count field is resolved via CrisisReviewCountLoader. This is the dominant
        # cost of the default (created_at) list.
        review_figures_count = Crisis.annotate_review_figures_count()
        if self.ordering_fields & set(review_figures_count.keys()):
            queryset = queryset.annotate(**review_figures_count)

        # event_count is resolved via EventCountLoader unless the list is ordered by it.
        if "event_count" in self.ordering_fields:
            queryset = queryset.annotate(event_count=Count("events"))

        # NOTE: no prefetch_related("events"): CrisisType exposes `events` as a paginated
        # dataloader field (apps/crisis/schema.py), not root.events.all(), and event_count
        # resolves via EventCountLoader. Nothing serializes root.events, so the eager
        # prefetch only ran an extra query + hydrated every event of the listed crises for
        # nothing (~1.8k event rows across the crisis list).
        return queryset


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
