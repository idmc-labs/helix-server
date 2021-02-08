import graphene

from apps.crisis.models import Crisis

from utils.enums import enum_description

CrisisTypeGrapheneEnum = graphene.String  # graphene.Enum.from_enum(Crisis.CRISIS_TYPE,
# description=enum_description)
