import typing

from typing_extensions import Annotated

from .constants import (
    CRISIS_TYPE,
    DATE_ACCURACY,
    EVENT_CODE_TYPE,
    FIGURE_CATEGORY_TYPES,
    FIGURE_DISPLACEMENT_OCCURRED,
    FIGURE_LOCATION_ACCURACY,
    FIGURE_LOCATION_GEOCODER,
    FIGURE_LOCATION_IDENTIFIER,
    FIGURE_QUANTIFIER,
    FIGURE_ROLE,
    FIGURE_TERMS,
    FIGURE_UNIT,
    HULK_BULK_IMPORT_STATUS,
)
from .parsers import enum_parser, json_parser

# TODO: Use proper naming - add prefix for pydantic validators?
DateAccuracy = Annotated[DATE_ACCURACY, enum_parser(DATE_ACCURACY)]
ListOfIds = Annotated[typing.List[int], json_parser()]

EventType = Annotated[CRISIS_TYPE, enum_parser(CRISIS_TYPE)]
EventCodeType = Annotated[EVENT_CODE_TYPE, enum_parser(EVENT_CODE_TYPE)]

FigureCategoryType = Annotated[FIGURE_CATEGORY_TYPES, enum_parser(FIGURE_CATEGORY_TYPES)]
FigureTermType = Annotated[FIGURE_TERMS, enum_parser(FIGURE_TERMS)]
FigureQuantifierType = Annotated[FIGURE_QUANTIFIER, enum_parser(FIGURE_QUANTIFIER)]
FigureUnitType = Annotated[FIGURE_UNIT, enum_parser(FIGURE_UNIT)]
FigureRoleType = Annotated[FIGURE_ROLE, enum_parser(FIGURE_ROLE)]
FigureDisplacementOccurredType = Annotated[FIGURE_DISPLACEMENT_OCCURRED, enum_parser(FIGURE_DISPLACEMENT_OCCURRED)]

FigureLocationIdentifierType = Annotated[FIGURE_LOCATION_IDENTIFIER, enum_parser(FIGURE_LOCATION_IDENTIFIER)]
FigureLocationGeocoderType = Annotated[FIGURE_LOCATION_GEOCODER, enum_parser(FIGURE_LOCATION_GEOCODER)]
FigureLocationAccuracyType = Annotated[FIGURE_LOCATION_ACCURACY, enum_parser(FIGURE_LOCATION_ACCURACY)]

HulkBulkImportStatusField = Annotated[HULK_BULK_IMPORT_STATUS, enum_parser(HULK_BULK_IMPORT_STATUS)]
