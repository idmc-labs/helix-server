import graphene

from apps.parking_lot.models import ParkingLot

from utils.enums import enum_description

ParkingLotGrapheneEnum = graphene.Enum.from_enum(ParkingLot.PARKING_LOT_STATUS,
                                                 description=enum_description)
