from django.utils.translation import gettext, gettext_lazy as _
from rest_framework import serializers

from apps.review.models import UnifiedReviewComment
from apps.contrib.serializers import MetaInformationSerializerMixin

NOT_ALLOWED_TO_REVIEW = _('You are not allowed to review this entry.')


class UnifiedReviewCommentSerializer(MetaInformationSerializerMixin,
                              serializers.ModelSerializer):
    class Meta:
        model = UnifiedReviewComment
        fields = '__all__'

    def validate_comment(self, comment: str):
        # we will store null for empty bodies
        if not  comment.strip():
            return None
        return comment

    def validate_comment_without_reviews(self, attrs):
        if not attrs.get('comment', '').strip():
            raise serializers.ValidationError(dict(comment='Comment is empty.'))

    def validate(self, attrs) -> dict:
        self.validate_comment_without_reviews(attrs)
        return super().validate(attrs)
