from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.parking_lot.models import ParkingLot


class ParkingLotSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ParkingLot
        fields = '__all__'
