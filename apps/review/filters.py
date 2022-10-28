from django_filters import rest_framework as df
from utils.filters import IDListFilter
from apps.review.models import UnifiedReviewComment


class UnifiedReviewCommentFilter(df.FilterSet):
    events = IDListFilter(method='filter_events')
    figures= IDListFilter(method='filter_figures')

    def filter_events(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(event__in=value)

    def filter_figures(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(reviews__figure__in=value)

    class Meta:
        model = UnifiedReviewComment
        fields = ('event', )

    @property
    def qs(self):
        return super().qs.filter(comment__isnull=False)
