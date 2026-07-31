import graphene
from django.db.models import Count, Exists, Max, Min, OuterRef
from django.db.models.sql.constants import LOUTER
from django.http import HttpRequest
from django_cte import With

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
    AcceptsOrdering,
    IDListFilter,
    MultiWordSearchFilterSet,
    SimpleInputFilter,
    StringListFilter,
    generate_type_for_filter_set,
)


class CrisisFilter(AcceptsOrdering, MultiWordSearchFilterSet):
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
        # nd/idp totals are annotated only when needed: aggregate_figures set, or sorting by them
        # (else resolvers read the default dataloaders). Both cases use the set-based CTE — a grouped
        # scan over the figures grouped by crisis. aggregate_figures passes its filtered figure_qs +
        # reference date (scoped totals); the sort path uses the default scope. This replaces the
        # per-crisis correlated subqueries re-scanned once per page row (260ms -> 93ms on a 50-row
        # page).
        figure_count_sort_fields = {Crisis.ND_FIGURES_ANNOTATE, Crisis.IDP_FIGURES_ANNOTATE}
        has_figure_scope = figure_qs is not None
        if has_figure_scope:
            queryset = Crisis.annotate_total_figure_disaggregation_via_cte(
                queryset, figures=figure_qs, reference_date=reference_date
            )
        elif self.ordering_fields & figure_count_sort_fields:
            queryset = Crisis.annotate_total_figure_disaggregation_via_cte(queryset)

        # The review-figure counts are an expensive fan-out aggregation over the whole
        # Figure table (Count over a crisis->event->figure join + GroupAggregate). They are
        # only needed in the queryset when the list is ordered by one of them; otherwise the
        # review_count field is resolved via CrisisReviewCountLoader. This is the dominant
        # cost of the default (created_at) list.
        review_figures_count = Crisis.annotate_review_figures_count()
        if self.ordering_fields & set(review_figures_count.keys()):
            queryset = queryset.annotate(**review_figures_count)

        # Crisis never got the denormalisation EventFilter has, so ordering by this M2M path
        # JOIN-fanned-out one crisis into one row per country. Denormalise the sort key into
        # a per-crisis scalar and alias it to the ordering token, exactly as event/entry do.
        # Min ascending / Max descending: that is the country the fan-out join sorted the
        # crisis at (see EventFilter.qs for the full reasoning).
        if "countries__idmc_short_name" in self.ordering_fields:
            sort_key = Max if "countries__idmc_short_name" in self.descending_ordering_fields else Min
            cte = With(
                Crisis.objects.values("id").annotate(countries_idmc_short_name=sort_key("countries__idmc_short_name")),
                name="crisis_countries_name_agg",
            )
            queryset = (
                cte.join(queryset, id=cte.col.id, _join_type=LOUTER)
                .with_cte(cte)
                .annotate(**{"countries__idmc_short_name": cte.col.countries_idmc_short_name})
            )

        # event_count is resolved via EventCountLoader unless the list is ordered by it.
        # distinct: when a review-figure count is annotated too, it aggregates
        # `events__figures`, and Django reuses the `events` join — so a bare Count would
        # count figure rows. The ordering would then disagree with the eventCount values the
        # client is shown, which come from EventCountLoader.
        if "event_count" in self.ordering_fields:
            queryset = queryset.annotate(event_count=Count("events", distinct=True))

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
