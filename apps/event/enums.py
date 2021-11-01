__all__ = ['EventOtherSubTypeEnum']

import graphene

from apps.event.models import Event

from utils.enums import enum_description
from apps.common.enums import QA_RULE_TYPE

EventOtherSubTypeEnum = graphene.Enum.from_enum(Event.EVENT_OTHER_SUB_TYPE,
                                                description=enum_description)
QaRecommendedFigureEnum = graphene.Enum.from_enum(QA_RULE_TYPE, description=enum_description)

enum_map = dict(
    EVENT_OTHER_SUB_TYPE=EventOtherSubTypeEnum,
    QA_RULE_TYPE=QaRecommendedFigureEnum,
)
