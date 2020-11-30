from django.test import RequestFactory

from apps.review.models import ReviewComment, Review
from apps.users.roles import MONITORING_EXPERT_EDITOR
from apps.review.serializers import ReviewCommentSerializer
from utils.factories import EntryFactory, ReviewFactory
from utils.tests import HelixTestCase, create_user_with_role


class TestReviewCommentSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.entry = EntryFactory.create()
        self.field1 = 'abc'
        self.field2 = 'def'
        self.field3 = 'xyz'
        self.red = Review.REVIEW_STATUS.RED.value
        self.green = Review.REVIEW_STATUS.GREEN.value
        self.data = dict(
            body='a new message',
            entry=self.entry.id,
            reviews=[
                dict(entry=self.entry.id, field=self.field1, value=self.red),
                dict(entry=self.entry.id, field=self.field2, value=self.green),
            ]
        )
        self.factory = RequestFactory()
        self.request = self.factory.get('/graphql')
        self.request.user = create_user_with_role(MONITORING_EXPERT_EDITOR)

    def test_valid_comment_with_reviews_creation(self):
        serializer = ReviewCommentSerializer(data=self.data,
                                             context={'request': self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        instance = serializer.save()
        self.assertEqual(instance.body, self.data['body'])
        self.assertEqual(instance.reviews.count(), len(self.data['reviews']))

    def test_invalid_duplicate_review_content(self):
        self.data['reviews'] = [
            dict(entry=self.entry.id, field=self.field1, value=self.red),
            # duplicates below
            dict(entry=self.entry.id, field=self.field2, value=self.green),
            dict(entry=self.entry.id, field=self.field2, value=self.green),
        ]
        serializer = ReviewCommentSerializer(data=self.data,
                                             context={'request': self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('reviews', serializer.errors)
