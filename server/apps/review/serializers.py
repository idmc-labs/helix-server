from rest_framework import serializers

from apps.review.models import Review, ReviewComment
from contrib.serializers import MetaInformationSerializerMixin


class ReviewSerializer(MetaInformationSerializerMixin,
                       serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'


class ReviewCommentSerializer(MetaInformationSerializerMixin,
                              serializers.ModelSerializer):
    reviews = ReviewSerializer(many=True)

    class Meta:
        models = ReviewComment
        fields = '__all__'

    def create(self, validated_data):
        reviews_data = validated_data.pop('reviews', [])
        review_comment = super().create(validated_data)
        Review.objects.bulk_create([
            Review(**review, comment_id=review_comment.id) for review in reviews_data
        ])
        return review_comment
