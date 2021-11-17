__all__ = ['QuantifierGrapheneEnum', 'UnitGrapheneEnum',
           'RoleGrapheneEnum', 'EntryReviewerGrapheneEnum',
           'OSMAccuracyGrapheneEnum', 'IdentifierGrapheneEnum']

import graphene

from apps.entry.models import (
    Figure,
    EntryReviewer,
    OSMName,
    FigureDisaggregationAbstractModel,
)

from utils.enums import enum_description
from apps.common.enums import GENDER_TYPE

DisplacementTypeGrapheneEnum = graphene.Enum.from_enum(
    FigureDisaggregationAbstractModel.DISPLACEMENT_TYPE,
    description=enum_description
)
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
EntryReviewerGrapheneEnum = graphene.Enum.from_enum(EntryReviewer.REVIEW_STATUS,
                                                    description=enum_description)
OSMAccuracyGrapheneEnum = graphene.Enum.from_enum(OSMName.OSM_ACCURACY,
                                                  description=enum_description)
IdentifierGrapheneEnum = graphene.Enum.from_enum(OSMName.IDENTIFIER, description=enum_description)
FigureCategoryTypeEnum = graphene.Enum.from_enum(Figure.FIGURE_CATEGORY_TYPES, description=enum_description)
FigureTermsEnum = graphene.Enum.from_enum(Figure.FIGURE_TERMS, description=enum_description)


enum_map = dict(
    DISPLACEMENT_TYPE=DisplacementTypeGrapheneEnum,
    GENDER_TYPE=GenderTypeGrapheneEnum,
    QUANTIFIER=QuantifierGrapheneEnum,
    UNIT=UnitGrapheneEnum,
    ROLE=RoleGrapheneEnum,
    DISPLACEMENT_OCCURRED=DisplacementOccurredGrapheneEnum,
    REVIEW_STATUS=EntryReviewerGrapheneEnum,
    OSM_ACCURACY=OSMAccuracyGrapheneEnum,
    IDENTIFIER=IdentifierGrapheneEnum,
    FIGURE_CATEGORY_TYPES=FigureCategoryTypeEnum,
    FIGURE_TERMS=FigureTermsEnum,
)
