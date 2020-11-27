import graphene

from apps.review.models import Review

from utils.enums import enum_description

ReviewStatusEnum = graphene.Enum.from_enum(Review.REVIEW_STATUS, description=enum_description)
