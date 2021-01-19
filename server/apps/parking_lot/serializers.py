from rest_framework import serializers

from apps.parking_lot.models import ParkingLot


class ParkingLotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingLot
        fields = '__all__'

    def validate(self, attrs):
        attrs.update(dict(
            submitted_by=self.context['request'].user,
        ))
        return attrs
