import graphene

from apps.entry.models import Figure

from utils.enums import enum_description

QuantifierGrapheneEnum = graphene.Enum.from_enum(Figure.QUANTIFIER, description=enum_description)
UnitGrapheneEnum = graphene.Enum.from_enum(Figure.UNIT, description=enum_description)
TermGrapheneEnum = graphene.Enum.from_enum(Figure.TERM, description=enum_description)
TypeGrapheneEnum = graphene.Enum.from_enum(Figure.TYPE, description=enum_description)
RoleGrapheneEnum = graphene.Enum.from_enum(Figure.ROLE, description=enum_description)
