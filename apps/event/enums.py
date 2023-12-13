import graphene
from utils.enums import enum_description
from apps.event.models import Event, EventCode
from apps.common.enums import QA_RULE_TYPE

QaRecommendedFigureEnum = graphene.Enum.from_enum(QA_RULE_TYPE, description=enum_description)
EventReviewStatusEnum = graphene.Enum.from_enum(Event.EVENT_REVIEW_STATUS, description=enum_description)
EventCodeTypeGrapheneEnum = graphene.Enum.from_enum(EventCode.EVENT_CODE_TYPE, description=enum_description)

enum_map = dict(
    QA_RULE_TYPE=QaRecommendedFigureEnum,
    EVENT_REVIEW_STATUS=EventReviewStatusEnum,
    EVENT_CODE_TYPE=EventCodeTypeGrapheneEnum,
)
