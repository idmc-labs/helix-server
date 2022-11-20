from django_filters import rest_framework as df
from utils.filters import IDListFilter, StringListFilter
from apps.review.models import UnifiedReviewComment


class UnifiedReviewCommentFilter(df.FilterSet):
    events = IDListFilter(method='filter_events')
    figures = IDListFilter(method='filter_figures')
    fields = StringListFilter(method='filter_fields')

    def filter_events(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(event__in=value)

    def filter_figures(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(figure__in=value)

    def filter_fields(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                return qs.filter(field__in=value).distinct()
            return qs.filter(field__in=[
                UnifiedReviewComment.REVIEW_FIELD_TYPE.get(item).value for item in value
            ])
        return qs

    class Meta:
        model = UnifiedReviewComment
        fields = ()

    @property
    def qs(self):
        return super().qs.filter(comment__isnull=False)
