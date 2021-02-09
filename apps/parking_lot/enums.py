__all__ = ['ParkedItemGrapheneEnum']

import graphene

from apps.parking_lot.models import ParkedItem

from utils.enums import enum_description

ParkedItemGrapheneEnum = graphene.Enum.from_enum(ParkedItem.PARKING_LOT_STATUS,
                                                 description=enum_description)

enum_map = dict(
    PARKING_LOT_STATUS=ParkedItemGrapheneEnum
)
