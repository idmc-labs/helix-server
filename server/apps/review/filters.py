from django_filters import rest_framework as df

from apps.review.models import ReviewComment


class ReviewCommentFilter(df.FilterSet):
    class Meta:
        model = ReviewComment
        fields = ('entry', )

    @property
    def qs(self):
        return super().qs.filter(body__isnull=False)
