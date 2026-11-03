import graphene

from apps.common.enums import QA_RULE_TYPE
from apps.event.models import Event, EventCode
from utils.enums import enum_description

QaRecommendedFigureEnum = graphene.Enum.from_enum(QA_RULE_TYPE, description=enum_description)
EventReviewStatusEnum = graphene.Enum.from_enum(Event.EVENT_REVIEW_STATUS, description=enum_description)
EventCodeTypeGrapheneEnum = graphene.Enum.from_enum(EventCode.EVENT_CODE_TYPE, description=enum_description)
EventHazardIntensityUnitEnum = graphene.Enum.from_enum(Event.HAZARD_INTENSITY_UNIT, description=enum_description)
EventHazardFootprintGeometryTypeEnum = graphene.Enum.from_enum(
    Event.HAZARD_FOOTPRINT_GEOMETRY_TYPE, description=enum_description
)

enum_map = dict(
    QA_RULE_TYPE=QaRecommendedFigureEnum,
    EVENT_REVIEW_STATUS=EventReviewStatusEnum,
    EVENT_CODE_TYPE=EventCodeTypeGrapheneEnum,
    HAZARD_INTENSITY_UNIT=EventHazardIntensityUnitEnum,
    HAZARD_FOOTPRINT_GEOMETRY_TYPE=EventHazardFootprintGeometryTypeEnum,
)
