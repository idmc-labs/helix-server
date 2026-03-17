import graphene

from apps.country.models import HouseholdSizeCarryOverTask

HouseholdSizeEnum = graphene.Enum.from_enum(HouseholdSizeCarryOverTask.AHHS_CARRYOVER_OPERATION_STATUS)
