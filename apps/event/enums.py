import graphene
from utils.enums import enum_description
from apps.event.models import Event
from apps.common.enums import QA_RULE_TYPE

QaRecommendedFigureEnum = graphene.Enum.from_enum(QA_RULE_TYPE, description=enum_description)
EventReviewStatusEnum = graphene.Enum.from_enum(Event.EventReviewStatus, description=enum_description)

enum_map = dict(
    QA_RULE_TYPE=QaRecommendedFigureEnum,
    EventReviewStatus=EventReviewStatusEnum,
)
