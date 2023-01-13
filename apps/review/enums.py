__all__ = ['ReviewStatusEnum']

import graphene

from apps.review.models import Review, UnifiedReviewComment

from utils.enums import enum_description

ReviewStatusEnum = graphene.Enum.from_enum(Review.ENTRY_REVIEW_STATUS, description=enum_description)
ReviewFieldTypeEnum = graphene.Enum.from_enum(UnifiedReviewComment.REVIEW_FIELD_TYPE, description=enum_description)
ReviewCommentTypeEnum = graphene.Enum.from_enum(UnifiedReviewComment.REVIEW_COMMENT_TYPE, description=enum_description)

enum_map = dict(
    REVIEW_FIELD_STATUS=ReviewStatusEnum,
    REVIEW_FIELD_TYPE=ReviewFieldTypeEnum,
    REVIEW_COMMENT_TYPE=ReviewCommentTypeEnum,
)
