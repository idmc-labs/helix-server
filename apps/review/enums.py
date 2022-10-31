__all__ = ['ReviewStatusEnum']

import graphene

from apps.review.models import Review, ReviewComment, UnifiedReviewComment

from utils.enums import enum_description

ReviewStatusEnum = graphene.Enum.from_enum(Review.ENTRY_REVIEW_STATUS, description=enum_description)
ReviewFieldTypeEnum = graphene.Enum.from_enum(UnifiedReviewComment.ReviewFieldType, description=enum_description)
ReviewCommentTypeEnum = graphene.Enum.from_enum(UnifiedReviewComment.ReviewCommentType, description=enum_description)

enum_map = dict(
    REVIEW_FIELD_STATUS=ReviewStatusEnum,
    ReviewFieldType=ReviewFieldTypeEnum,
    ReviewCommentType=ReviewCommentTypeEnum,
)

