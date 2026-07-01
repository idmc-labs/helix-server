from collections import defaultdict

from django.contrib.postgres.aggregates.general import StringAgg
from django.db import models
from django.db.models import Case, CharField, F, Q, When
from promise import Promise
from promise.dataloader import DataLoader

from apps.common.utils import EXTERNAL_ARRAY_SEPARATOR
from apps.entry.models import Entry, Figure
from apps.review.models import UnifiedReviewComment


def batch_load_fn_by_category(keys, category):
    qs = Entry.objects.filter(id__in=keys).annotate(**Entry._total_figure_disaggregation_subquery())

    if category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT:
        qs = qs.annotate(_total=models.F(Entry.ND_FIGURES_ANNOTATE))
    else:
        qs = qs.annotate(_total=models.F(Entry.IDP_FIGURES_ANNOTATE))

    batch_load = {item["id"]: item["_total"] for item in qs.values("id", "_total")}

    return Promise.resolve([batch_load.get(key) for key in keys])


class TotalIDPFigureByEntryLoader(DataLoader):
    def batch_load_fn(self, keys):
        return batch_load_fn_by_category(keys, Figure.FIGURE_CATEGORY_TYPES.IDPS)


class TotalNDFigureByEntryLoader(DataLoader):
    def batch_load_fn(self, keys):
        return batch_load_fn_by_category(keys, Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT)


class FigureTypologyLoader(DataLoader):
    def batch_load_fn(self, keys: list):
        qs = (
            Figure.objects.filter(id__in=keys)
            .annotate(
                figure_typology=Case(
                    When(other_sub_type__isnull=False, then=F("other_sub_type__name")),
                    When(violence_sub_type__isnull=False, then=F("violence_sub_type__name")),
                    When(disaster_sub_type__isnull=False, then=F("disaster_sub_type__name")),
                    output_field=CharField(),
                )
            )
            .values("id", "figure_typology")
        )
        batch_load = {item["id"]: item["figure_typology"] for item in qs}
        return Promise.resolve([batch_load.get(key) for key in keys])


class FigureGeoLocationLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = (
            Figure.objects.filter(id__in=keys)
            .annotate(geolocations=StringAgg("geo_locations__display_name", EXTERNAL_ARRAY_SEPARATOR))
            .values("id", "geolocations")
        )
        batch_load = {item["id"]: item["geolocations"] for item in qs}
        return Promise.resolve([batch_load.get(key) for key in keys])


class FigureSourcesReliability(DataLoader):
    def batch_load_fn(self, keys):
        qs = (
            Figure.objects.filter(id__in=keys)
            .annotate(**Figure.annotate_sources_reliability())
            .values("id", "sources_reliability")
        )
        batch_load = {item["id"]: item["sources_reliability"] for item in qs}
        return Promise.resolve([batch_load.get(key) for key in keys])


class FigureLastReviewCommentStatusLoader(DataLoader):
    def batch_load_fn(self, keys):
        review_comment_qs = (
            UnifiedReviewComment.objects.filter(
                Q(figure__in=keys)
                and Q(
                    comment_type__in=[
                        UnifiedReviewComment.REVIEW_COMMENT_TYPE.GREEN,
                        UnifiedReviewComment.REVIEW_COMMENT_TYPE.RED,
                    ]
                )
            )
            .order_by(
                "figure_id",
                "field",
                "-id",
            )
            .distinct(
                "figure_id",
                "field",
            )
            .values(
                "id",
                "figure_id",
                "field",
                "comment_type",
            )
        )
        _map = defaultdict(list)
        for item in review_comment_qs:
            id = item["id"]
            field = item["field"]
            comment_type = item["comment_type"]
            _map[item["figure_id"]].append(
                {
                    "id": id,
                    "field": field,
                    "comment_type": comment_type,
                }
            )
        return Promise.resolve([_map[key] for key in keys])


class EntryFiguresLoader(DataLoader):
    """Batch-load the figures of each entry for EntryType.figures.

    EntryType.figures was resolved per-entry, so an entry list issued one figures
    query (plus its select_related/prefetch_related) for every row -> ~9 queries
    per entry (an N+1). This loads all figures for the batched entries in one query
    (the prefetches run once for the whole batch), then groups by entry_id. The
    select_related/prefetch_related set is identical to the old per-entry resolver,
    so each FigureType sees the same prefetched data; only the query count changes.
    """

    def batch_load_fn(self, keys: list):
        qs = (
            Figure.objects.filter(entry_id__in=keys)
            .select_related(
                "event",
                "violence",
                "violence_sub_type",
                "disaster_category",
                "disaster_sub_category",
                "disaster_type",
                "disaster_sub_type",
                "other_sub_type",
                "osv_sub_type",
                "approved_by",
                "country",
                "event__disaster_category",
                "event__disaster_sub_category",
                "event__disaster_type",
                "event__disaster_sub_type",
            )
            .prefetch_related(
                "tags",
                "context_of_violence",
                "event__disaster_sub_category",
                "event__countries",
                "event__context_of_violence",
                # NOTE: geo_locations / sources (+ sources__countries / __organization_kind)
                # are intentionally NOT prefetched: FigureType serves them via paginated
                # dataloader fields (DjangoPaginatedListObjectField), so they are never read
                # off the prefetched instance. Prefetching them only hydrated thousands of
                # rows (incl. the fat Organization table) for nothing — ~270ms of the ~600ms
                # spent here at pageSize 100.
            )
        )
        _map = defaultdict(list)
        for figure in qs:
            _map[figure.entry_id].append(figure)
        return Promise.resolve([_map.get(key, []) for key in keys])
