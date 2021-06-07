from django.test import RequestFactory

from apps.review.models import Review
from apps.users.enums import USER_ROLE
from apps.review.serializers import ReviewCommentSerializer
from utils.factories import EntryFactory
from utils.tests import HelixTestCase, create_user_with_role


class TestReviewCommentSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.entry = EntryFactory.create()
        self.field1 = 'abc'
        self.field2 = 'def'
        self.field3 = 'xyz'
        self.red = Review.ENTRY_REVIEW_STATUS.RED.value
        self.green = Review.ENTRY_REVIEW_STATUS.GREEN.value
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
        self.request.user = self.user = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT.name
        )
        self.entry.reviewers.set([self.user])

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

    def test_valid_user_not_in_reviewers_can_still_review(self):
        self.entry.reviewers.add(self.request.user)
        # user is already in the reviewers, he is allowed
        serializer = ReviewCommentSerializer(data=self.data,
                                             context={'request': self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        self.entry.reviewers.clear()
        # if user is trying to review is not in the reviewers, he is still allowed
        serializer = ReviewCommentSerializer(data=self.data,
                                             context={'request': self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        # if user is only trying to comment, he is allowed
        data = dict(
            body='a new body',
            entry=self.entry.id
        )
        serializer = ReviewCommentSerializer(data=data,
                                             context={'request': self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
