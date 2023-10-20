__all__ = ['QuantifierGrapheneEnum', 'UnitGrapheneEnum',
           'RoleGrapheneEnum', 'OSMAccuracyGrapheneEnum', 'IdentifierGrapheneEnum']

import graphene

from apps.entry.models import (
    Figure,
    OSMName,
    ExternalApiDump,
)

from utils.enums import enum_description
from apps.common.enums import GENDER_TYPE

GenderTypeGrapheneEnum = graphene.Enum.from_enum(
    GENDER_TYPE,
    description=enum_description
)
QuantifierGrapheneEnum = graphene.Enum.from_enum(Figure.QUANTIFIER, description=enum_description)
UnitGrapheneEnum = graphene.Enum.from_enum(Figure.UNIT, description=enum_description)
RoleGrapheneEnum = graphene.Enum.from_enum(Figure.ROLE, description=enum_description)
DisplacementOccurredGrapheneEnum = graphene.Enum.from_enum(
    Figure.DISPLACEMENT_OCCURRED,
    description=enum_description
)
OSMAccuracyGrapheneEnum = graphene.Enum.from_enum(OSMName.OSM_ACCURACY,
                                                  description=enum_description)
IdentifierGrapheneEnum = graphene.Enum.from_enum(OSMName.IDENTIFIER, description=enum_description)
FigureCategoryTypeEnum = graphene.Enum.from_enum(Figure.FIGURE_CATEGORY_TYPES, description=enum_description)
FigureTermsEnum = graphene.Enum.from_enum(Figure.FIGURE_TERMS, description=enum_description)
FigureSourcesReliabilityEnum = graphene.Enum.from_enum(Figure.SOURCES_RELIABILITY, description=enum_description)
FigureReviewStatusEnum = graphene.Enum.from_enum(Figure.FIGURE_REVIEW_STATUS, description=enum_description)
ExternalApiTypeEnum = graphene.Enum.from_enum(
    ExternalApiDump.ExternalApiType,
    description=enum_description
)


enum_map = dict(
    GENDER_TYPE=GenderTypeGrapheneEnum,
    QUANTIFIER=QuantifierGrapheneEnum,
    UNIT=UnitGrapheneEnum,
    ROLE=RoleGrapheneEnum,
    DISPLACEMENT_OCCURRED=DisplacementOccurredGrapheneEnum,
    OSM_ACCURACY=OSMAccuracyGrapheneEnum,
    IDENTIFIER=IdentifierGrapheneEnum,
    FIGURE_CATEGORY_TYPES=FigureCategoryTypeEnum,
    FIGURE_TERMS=FigureTermsEnum,
    SOURCES_RELIABILITY=FigureSourcesReliabilityEnum,
    FIGURE_REVIEW_STATUS=FigureReviewStatusEnum,
    EXTERNAL_API_TYPE=ExternalApiTypeEnum,
)
