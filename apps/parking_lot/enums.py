__all__ = ['ParkingLotStatusGrapheneEnum', 'ParkingLotSourceGrapheneEnum']

import graphene

from apps.parking_lot.models import ParkedItem

from utils.enums import enum_description

ParkingLotStatusGrapheneEnum = graphene.Enum.from_enum(
    ParkedItem.PARKING_LOT_STATUS,
    description=enum_description,
)

ParkingLotSourceGrapheneEnum = graphene.Enum.from_enum(
    ParkedItem.PARKING_LOT_SOURCE,
    description=enum_description,
)

enum_map = dict(
    PARKING_LOT_STATUS=ParkingLotStatusGrapheneEnum,
    PARKING_LOT_SOURCE=ParkingLotSourceGrapheneEnum,
)
