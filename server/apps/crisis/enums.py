import graphene

from apps.crisis.models import Crisis

CrisisTypeGrapheneEnum = graphene.Enum.from_enum(Crisis.CRISIS_TYPE)
