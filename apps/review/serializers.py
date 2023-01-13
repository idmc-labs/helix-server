from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.review.models import UnifiedReviewComment
from apps.contrib.serializers import MetaInformationSerializerMixin

NOT_ALLOWED_TO_REVIEW = _('You are not allowed to review this entry.')


class UnifiedReviewCommentSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = UnifiedReviewComment
        fields = (
            'event', 'geo_location', 'figure', 'field', 'comment_type', 'geo_location', 'comment',
        )

    def validate_comment(self, comment: str):
        # we will store null for empty bodies
        if not comment or not comment.strip():
            return None
        return comment

    def _validate_comment_without_reviews(self, attrs):
        comment = attrs.get('comment')
        comment_type = attrs.get('comment_type')
        if (not comment or not comment.strip()) and comment_type != UnifiedReviewComment.REVIEW_COMMENT_TYPE.GREEN:
            raise serializers.ValidationError(dict(comment=_('Comment is empty.')))

    def validate(self, attrs) -> dict:
        self._validate_comment_without_reviews(attrs)
        return super().validate(attrs)
