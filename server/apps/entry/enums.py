import graphene

from apps.entry.models import Figure

QuantifierGrapheneEnum = graphene.Enum.from_enum(Figure.QUANTIFIER)
UnitGrapheneEnum = graphene.Enum.from_enum(Figure.UNIT)
TermGrapheneEnum = graphene.Enum.from_enum(Figure.TERM)
TypeGrapheneEnum = graphene.Enum.from_enum(Figure.TYPE)
RoleGrapheneEnum = graphene.Enum.from_enum(Figure.ROLE)
