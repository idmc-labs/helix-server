import graphene

from apps.entry.models import Figure, EntryReviewer, OSMName

from utils.enums import enum_description

QuantifierGrapheneEnum = graphene.Enum.from_enum(Figure.QUANTIFIER, description=enum_description)
UnitGrapheneEnum = graphene.Enum.from_enum(Figure.UNIT, description=enum_description)
TermGrapheneEnum = graphene.Enum.from_enum(Figure.TERM, description=enum_description)
RoleGrapheneEnum = graphene.Enum.from_enum(Figure.ROLE, description=enum_description)
EntryReviewerGrapheneEnum = graphene.Enum.from_enum(EntryReviewer.REVIEW_STATUS,
                                                    description=enum_description)
OSMAccuracyGrapheneEnum = graphene.Enum.from_enum(OSMName.OSM_ACCURACY,
                                                  description=enum_description)
IdentifierGrapheneEnum = graphene.Enum.from_enum(OSMName.IDENTIFIER, description=enum_description)
