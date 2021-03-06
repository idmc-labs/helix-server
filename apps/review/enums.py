__all__ = ['ReviewStatusEnum']

import graphene

from apps.review.models import Review

from utils.enums import enum_description

ReviewStatusEnum = graphene.Enum.from_enum(Review.ENTRY_REVIEW_STATUS, description=enum_description)

enum_map = dict(
    ENTRY_REVIEW_STATUS=ReviewStatusEnum
)
