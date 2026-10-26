import graphene

from apps.country.models import HouseholdSize
from utils.enums import enum_description

HouseholdSizeGapFillingMethodEnum = graphene.Enum.from_enum(HouseholdSize.GAP_FILLING_METHOD, description=enum_description)


class HouseholdSizeStatusEnum(graphene.Enum):
    ALL = "ALL"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


enum_map = dict(
    GAP_FILLING_METHOD=HouseholdSizeGapFillingMethodEnum,
)
