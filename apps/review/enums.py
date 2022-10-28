__all__ = ['ReviewStatusEnum']

import graphene

from apps.review.models import Review, ReviewComment, UnifiedReviewComment

from utils.enums import enum_description

ReviewStatusEnum = graphene.Enum.from_enum(Review.ENTRY_REVIEW_STATUS, description=enum_description)
FieldTypeEnum = graphene.Enum.from_enum(UnifiedReviewComment.ReviewFieldType, description=enum_description)
ReviewCommentStatusEnum = graphene.Enum.from_enum(UnifiedReviewComment.ReviewCommentStatus, description=enum_description)

enum_map = dict(
    REVIEW_FIELD_STATUS=ReviewStatusEnum,
    FieldType=FieldTypeEnum,
    ReviewFieldStatus=ReviewCommentStatusEnum,
)

