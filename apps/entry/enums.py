__all__ = ['QuantifierGrapheneEnum', 'UnitGrapheneEnum',
           'RoleGrapheneEnum', 'EntryReviewerGrapheneEnum',
           'OSMAccuracyGrapheneEnum', 'IdentifierGrapheneEnum']

import graphene

from apps.entry.models import Figure, EntryReviewer, OSMName
from apps.entry.constants import (
    DISAGGREGATED_AGE_SEX_CHOICES,
)

from utils.enums import enum_description

QuantifierGrapheneEnum = graphene.Enum.from_enum(Figure.QUANTIFIER, description=enum_description)
UnitGrapheneEnum = graphene.Enum.from_enum(Figure.UNIT, description=enum_description)
RoleGrapheneEnum = graphene.Enum.from_enum(Figure.ROLE, description=enum_description)
DisplacementOccurredGrapheneEnum = graphene.Enum.from_enum(
    Figure.DISPLACEMENT_OCCURRED,
    description=enum_description
)
EntryReviewerGrapheneEnum = graphene.Enum.from_enum(EntryReviewer.REVIEW_STATUS,
                                                    description=enum_description)
OSMAccuracyGrapheneEnum = graphene.Enum.from_enum(OSMName.OSM_ACCURACY,
                                                  description=enum_description)
IdentifierGrapheneEnum = graphene.Enum.from_enum(OSMName.IDENTIFIER, description=enum_description)
DisaggregatedAgeSexGrapheneEnum = graphene.Enum.from_enum(DISAGGREGATED_AGE_SEX_CHOICES, description=enum_description)

enum_map = dict(
    QUANTIFIER=QuantifierGrapheneEnum,
    UNIT=UnitGrapheneEnum,
    ROLE=RoleGrapheneEnum,
    DISPLACEMENT_OCCURRED=DisplacementOccurredGrapheneEnum,
    REVIEW_STATUS=EntryReviewerGrapheneEnum,
    OSM_ACCURACY=OSMAccuracyGrapheneEnum,
    IDENTIFIER=IdentifierGrapheneEnum,
    DISAGGREGATED_AGE_SEX_CHOICES=DisaggregatedAgeSexGrapheneEnum,
)
