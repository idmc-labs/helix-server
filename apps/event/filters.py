import django_filters
import graphene
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.db import models
from django.db.models import Count, Max, Min, Q
from django.db.models.sql.constants import LOUTER
from django.http import HttpRequest
from django_cte import With

from apps.common.enums import QA_RULE_TYPE
from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.event.constants import OSV
from apps.event.models import (
    Actor,
    ContextOfViolence,
    DisasterCategory,
    DisasterSubCategory,
    DisasterSubType,
    DisasterType,
    Event,
    OsvSubType,
    OtherSubType,
    Violence,
    ViolenceSubType,
)
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
    IDFilter,
    IDListFilter,
    MultiWordSearchFilterSet,
    SimpleInputFilter,
    StringListFilter,
    generate_type_for_filter_set,
)


class EventFilter(MultiWordSearchFilterSet):
    # Opt-in: DjangoPaginatedListObjectField uses this marker to decide whether
    # to forward the active ordering as a constructor arg, so we can gate
    # expensive annotations on it (see qs property below).
    accepts_ordering = True

    crisis_by_ids = IDListFilter(method="filter_crises")
    event_types = StringListFilter(method="filter_event_types")
    countries = IDListFilter(method="filter_countries")

    osv_sub_type_by_ids = IDListFilter(method="filter_osv_sub_types")
    # used in report entry table
    disaster_sub_types = IDListFilter(method="filter_disaster_sub_types")
    violence_types = IDListFilter(method="filter_violence_types")
    violence_sub_types = IDListFilter(method="filter_violence_sub_types")
    created_by_ids = IDListFilter(method="filter_created_by")
    qa_rule = django_filters.CharFilter(method="filter_qa_rule")
    context_of_violences = IDListFilter(method="filter_context_of_violences")
    review_status = StringListFilter(method="filter_review_status")
    assignees = IDListFilter(method="filter_assignees")
    assigners = IDListFilter(method="filter_assigners")

    filter_figures = SimpleInputFilter(FigureExtractionFilterDataInputType, method="filter_by_figures")
    aggregate_figures = SimpleInputFilter(FigureAggregateFilterDataInputType, method="noop")

    request: HttpRequest

    class Meta:
        model = Event
        fields = {
            "created_at": ["lte", "lt", "gte", "gt"],
            "start_date": ["lte", "lt", "gte", "gt"],
            "end_date": ["lte", "lt", "gte", "gt"],
            "ignore_qa": ["exact"],
        }
        # NOTE: event_code__event_code is not using exact match
        multi_word_search_fields = ["name", "event_code__event_code"]

    def __init__(self, *args, ordering=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ordering_fields = {field.lstrip("-") for field in ordering.split(",") if field} if ordering else set()
        # A denormalised to-many sort key depends on the direction it is sorted in, which
        # `ordering_fields` has stripped off.
        self.descending_ordering_fields = (
            {field[1:] for field in ordering.split(",") if field.startswith("-")} if ordering else set()
        )

    def noop(self, qs, name, value):
        return qs

    def filter_by_figures(self, qs, _, value):
        return FigureFilterHelper.filter_using_figure_filters(qs, value, self.request)

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        # M2M: test membership with Exists (no join fan-out) so no .distinct() is needed.
        return qs.filter(
            models.Exists(Event.countries.through.objects.filter(event_id=models.OuterRef("pk"), country_id__in=value))
        )

    def filter_disaster_sub_types(self, qs, name, value):
        if not value:
            return qs
        # disaster_sub_type is a to-one FK: the join can't fan out, so no .distinct().
        return qs.filter(~Q(event_type=Crisis.CRISIS_TYPE.DISASTER.value) | Q(disaster_sub_type__in=value))

    def filter_violence_types(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(~Q(event_type=Crisis.CRISIS_TYPE.CONFLICT.value) | Q(violence__in=value))

    def filter_violence_sub_types(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(~Q(event_type=Crisis.CRISIS_TYPE.CONFLICT.value) | Q(violence_sub_type__in=value))

    def filter_crises(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(crisis__in=value)

    def filter_event_types(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # internal filtering
                return qs.filter(event_type__in=value)
            return qs.filter(event_type__in=[Crisis.CRISIS_TYPE.get(item).value for item in value])
        return qs

    def filter_review_status(self, qs, name, value):
        # Filter out *_BUT_CHANGED values from user input
        value = [
            v
            for v in value or []
            if v
            not in [
                Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED.value,
                Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED.name,
                Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED.value,
                Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED.name,
            ]
        ]
        if value:
            if (
                Event.EVENT_REVIEW_STATUS.REVIEW_IN_PROGRESS.value in value
                or Event.EVENT_REVIEW_STATUS.REVIEW_IN_PROGRESS.name in value
            ):
                # Add *_BUT_CHANGED values if REVIEW_IN_PROGRESS is provided by user
                value = [
                    *value,
                    Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED.value,
                    Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED.value,
                ]
            if isinstance(value[0], int):
                return qs.filter(review_status__in=value)
            return qs.filter(
                review_status__in=[
                    # NOTE: item is string. eg: 'REVIEW_IN_PROGRESS'
                    Event.EVENT_REVIEW_STATUS.get(item).value
                    for item in value
                ]
            )
        return qs

    def filter_osv_sub_types(self, qs, name, value):
        if value:
            return qs.filter(~Q(violence__name=OSV) | Q(osv_sub_type__in=value))
        return qs

    def filter_qa_rule(self, qs, name, value):
        if QA_RULE_TYPE.HAS_NO_RECOMMENDED_FIGURES.name == value:
            return qs.annotate(
                figure_count=Count(
                    "figures",
                    filter=Q(
                        figures__category__in=[
                            Figure.FIGURE_CATEGORY_TYPES.IDPS,
                            Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                        ],
                        ignore_qa=False,
                        figures__role=Figure.ROLE.RECOMMENDED,
                        figures__geo_locations__isnull=False,
                    ),
                )
            ).filter(figure_count=0)
        elif QA_RULE_TYPE.HAS_MULTIPLE_RECOMMENDED_FIGURES.name == value:
            events_id_qs = (
                Figure.objects.filter(
                    category__in=[
                        Figure.FIGURE_CATEGORY_TYPES.IDPS,
                        Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                    ],
                    event__ignore_qa=False,
                    role=Figure.ROLE.RECOMMENDED,
                    geo_locations__isnull=False,
                )
                .annotate(
                    locations=models.Subquery(
                        Figure.geo_locations.through.objects.filter(figure=models.OuterRef("pk"))
                        .order_by()
                        .values("figure")
                        .annotate(
                            locations=ArrayAgg("figurelocation__name", distinct=True, ordering="figurelocation__name"),
                        )
                        .values("locations")[:1],
                        output_field=models.CharField(),
                    ),
                )
                .order_by()
                .values("event", "category", "locations")
                .annotate(
                    count=Count("id", distinct=True),
                )
            )
            return qs.filter(id__in=events_id_qs.filter(count__gt=1).values("event").distinct())
        return qs

    def filter_context_of_violences(self, qs, name, value):
        if not value:
            return qs
        # M2M: Exists membership test, no fan-out -> no .distinct() needed.
        return qs.filter(
            models.Exists(
                Event.context_of_violence.through.objects.filter(
                    event_id=models.OuterRef("pk"), contextofviolence_id__in=value
                )
            )
        )

    def filter_assigners(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(assigner__in=value)

    def filter_assignees(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(assignee__in=value)

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
        # (else resolvers read the default dataloaders). We need BOTH a subquery and a CTE; a CTE
        # alone can't do it — it is fixed to the default unfiltered scope, so aggregate_figures'
        # filtered values must come from the parametrized subquery. The CTE is just the faster
        # set-based path for the default values when sorting (big win on event; crisis/country are
        # low-cardinality, so ~neutral there, kept for parity).
        # TODO: move aggregate_figures onto dataloaders -> the subquery arm goes away.
        figure_disaggregation = Event._total_figure_disaggregation_subquery(
            figures=figure_qs,
            reference_date=reference_date,
        )
        figure_count_sort_fields = {Event.ND_FIGURES_ANNOTATE, Event.IDP_FIGURES_ANNOTATE}
        has_figure_scope = figure_qs is not None
        if has_figure_scope:
            queryset = queryset.annotate(**figure_disaggregation)
        elif self.ordering_fields & figure_count_sort_fields:
            queryset = Event.annotate_total_figure_disaggregation_via_cte(queryset)

        # The review-figure counts are an expensive fan-out aggregation over the whole
        # Figure table (Count over a join + GroupAggregate). They are only needed in the
        # queryset when the list is ordered by one of them; otherwise the review_count
        # field is resolved via EventReviewCountLoader. This is the dominant cost of the
        # default (created_at) list.
        review_figures_count = Event.annotate_review_figures_count()
        if self.ordering_fields & set(review_figures_count.keys()):
            queryset = queryset.annotate(**review_figures_count)

        # entry_count is resolved via EventEntryCountLoader unless ordered by it.
        if "entry_count" in self.ordering_fields:
            queryset = queryset.annotate(
                entry_count=models.Subquery(
                    Figure.objects.filter(event=models.OuterRef("pk"))
                    .order_by()
                    .values("event")
                    .annotate(count=models.Count("entry", distinct=True))
                    .values("count")[:1],
                    output_field=models.IntegerField(),
                ),
            )

        # Ordering by `countries__idmc_short_name` (M2M) would JOIN-fan-out one event into
        # one row per country. Denormalize the sort key into a per-event scalar via a
        # whole-table CTE, LEFT JOIN by id, and order by that scalar — one row per event,
        # deterministic, no global DISTINCT. Alias == the ordering token so
        # order_by("countries__idmc_short_name") binds to this annotation, not the M2M path.
        #
        # The scalar is Min or Max of the country name, picked by the sort direction, because
        # that is exactly where the fan-out join placed the event: sorting all its duplicated
        # rows ascending, the event first appears at its alphabetically smallest country;
        # descending, at its greatest. Any other reduction (a concatenation of all the names,
        # say) changes the ranking — descending would rank by the smallest name reversed, and
        # ascending would break ties between a name and a name that prefixes it.
        if "countries__idmc_short_name" in self.ordering_fields:
            sort_key = Max if "countries__idmc_short_name" in self.descending_ordering_fields else Min
            cte = With(
                Event.objects.values("id").annotate(countries_idmc_short_name=sort_key("countries__idmc_short_name")),
                name="event_countries_name_agg",
            )
            queryset = (
                cte.join(queryset, id=cte.col.id, _join_type=LOUTER)
                .with_cte(cte)
                .annotate(**{"countries__idmc_short_name": cte.col.countries_idmc_short_name})
            )

        # NOTE: no prefetch_related("figures"): EventType excludes the `figures` field
        # (apps/event/schema.py), and the figure-count fields resolve via annotations or
        # dataloaders, so nothing serializes root.figures. prefetch_related is eager, so
        # keeping it ran an extra query + hydrated every figure of the page's events for
        # nothing (~211 figure rows at pageSize 100). context_of_violence IS an exposed
        # field, so it stays.
        return queryset.prefetch_related("context_of_violence")


class ActorFilter(MultiWordSearchFilterSet):
    class Meta:
        model = Actor
        fields = []
        multi_word_search_fields = ["name"]


class DisasterSubTypeFilter(MultiWordSearchFilterSet):
    class Meta:
        model = DisasterSubType
        fields = []
        multi_word_search_fields = ["name"]


class DisasterTypeFilter(MultiWordSearchFilterSet):
    class Meta:
        model = DisasterType
        fields = []
        multi_word_search_fields = ["name"]


class DisasterCategoryFilter(MultiWordSearchFilterSet):
    class Meta:
        model = DisasterCategory
        fields = []
        multi_word_search_fields = ["name"]


class DisasterSubCategoryFilter(MultiWordSearchFilterSet):
    class Meta:
        model = DisasterSubCategory
        fields = []
        multi_word_search_fields = ["name"]


class OsvSubTypeFilter(MultiWordSearchFilterSet):
    class Meta:
        model = OsvSubType
        fields = []
        multi_word_search_fields = ["name"]


class OtherSubTypeFilter(MultiWordSearchFilterSet):
    class Meta:
        model = OtherSubType
        fields = []
        multi_word_search_fields = ["name"]


class ContextOfViolenceFilter(MultiWordSearchFilterSet):
    class Meta:
        model = ContextOfViolence
        fields = []
        multi_word_search_fields = ["name"]


class ViolenceFilter(django_filters.FilterSet):
    id = IDFilter(field_name="id", lookup_expr="exact")

    class Meta:
        model = Violence
        fields = []


class ViolenceSubTypeFilter(django_filters.FilterSet):
    id = IDFilter(field_name="id", lookup_expr="exact")

    class Meta:
        model = ViolenceSubType
        fields = []


EventFilterDataType, EventFilterDataInputType = generate_type_for_filter_set(
    EventFilter,
    "event.schema.event_list",
    "EventFilterDataType",
    "EventFilterDataInputType",
    custom_new_fields_map={
        "filter_figures": graphene.Field(FigureExtractionFilterDataType),
        "aggregate_figures": graphene.Field(FigureAggregateFilterDataType),
    },
)

ActorFilterDataType, ActorFilterDataInputType = generate_type_for_filter_set(
    ActorFilter,
    "event.schema.actor_list",
    "ActorFilterDataType",
    "ActorFilterDataInputType",
)

ContextOfViolenceFilterDataType, ContextOfViolenceFilterDataInputType = generate_type_for_filter_set(
    ContextOfViolenceFilter,
    "event.schema.context_of_violence_list",
    "ContextOfViolenceFilterDataType",
    "ContextOfViolenceFilterDataInputType",
)
