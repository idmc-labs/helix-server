from rest_framework import serializers

from apps.review.models import Review, ReviewComment
from apps.contrib.serializers import MetaInformationSerializerMixin


class ReviewSerializer(MetaInformationSerializerMixin,
                       serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'


class ReviewCommentSerializer(MetaInformationSerializerMixin,
                              serializers.ModelSerializer):
    reviews = ReviewSerializer(many=True)

    class Meta:
        model = ReviewComment
        fields = '__all__'

    def validate_reviews(self, reviews):
        if len(reviews) != len(set([(
            each.get('figure'),
            each.get('field'),
            each.get('age_id'),
            each.get('strata_id')
        ) for each in reviews])):
            raise serializers.ValidationError('Unique reviews are expected from a single comment.')
        return reviews

    def create(self, validated_data):
        reviews_data = validated_data.pop('reviews', [])
        review_comment = super().create(validated_data)
        Review.objects.bulk_create([
            Review(**review,
                   entry_id=review_comment.entry.id,
                   comment_id=review_comment.id) for review in reviews_data
        ])
        return review_comment
