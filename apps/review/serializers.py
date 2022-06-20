from django.utils.translation import gettext, gettext_lazy as _
from rest_framework import serializers

from apps.review.models import Review, ReviewComment
from apps.contrib.serializers import MetaInformationSerializerMixin

NOT_ALLOWED_TO_REVIEW = _('You are not allowed to review this entry.')


class ReviewSerializer(MetaInformationSerializerMixin,
                       serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ('id', 'entry', 'figure', 'field', 'value', 'age', 'geo_location', 'comment')


class ReviewCommentSerializer(MetaInformationSerializerMixin,
                              serializers.ModelSerializer):
    reviews = ReviewSerializer(many=True, required=False)

    class Meta:
        model = ReviewComment
        fields = '__all__'

    def validate_reviews(self, reviews):
        if len(reviews) != len(set([tuple([
            each.get(field) for field in Review.UNIQUE_TOGETHER_FIELDS
        ]) for each in reviews])):
            raise serializers.ValidationError(
                gettext('Unique reviews are expected from a single comment.')
            )
        return reviews

    def validate_body(self, body: str):
        # we will store null for empty bodies
        if not body.strip():
            return None
        return body

    def validate_body_without_reviews(self, attrs):
        if not attrs.get('reviews') and not attrs.get('body', '').strip():
            raise serializers.ValidationError(dict(body='Comment is empty.'))

    def validate(self, attrs) -> dict:
        self.validate_body_without_reviews(attrs)
        return super().validate(attrs)

    def create(self, validated_data):
        reviews_data = validated_data.pop('reviews', [])
        review_comment = super().create(validated_data)
        if reviews_data:
            Review.objects.bulk_create([
                Review(
                    **review,
                    created_by_id=review_comment.created_by.id,
                    entry_id=review_comment.entry.id,
                    comment_id=review_comment.id
                )
                for review in reviews_data
            ])
        return review_comment
