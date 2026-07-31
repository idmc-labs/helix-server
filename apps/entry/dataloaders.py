from collections import defaultdict

from django.contrib.postgres.aggregates.general import StringAgg
from django.db.models import Case, CharField, F, Q, When
from promise import Promise
from promise.dataloader import DataLoader

from apps.common.utils import EXTERNAL_ARRAY_SEPARATOR
from apps.entry.models import Figure
from apps.review.models import UnifiedReviewComment


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
