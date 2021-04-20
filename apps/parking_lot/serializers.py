from rest_framework import serializers

from apps.contrib.serializers import (
    MetaInformationSerializerMixin,
    UpdateSerializerMixin,
    IntegerIDField,
)
from apps.parking_lot.models import ParkedItem
from apps.country.models import Country


class ParkedItemSerializer(MetaInformationSerializerMixin,
                           serializers.ModelSerializer):
    country_iso3 = serializers.CharField(required=False)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)

    class Meta:
        model = ParkedItem
        fields = '__all__'

    def validate(self, data):
        data = super().validate(data)
        iso3 = data.get('country_iso3')
        if iso3 and not Country.objects.filter(iso3=iso3).exists():
            raise serializers.ValidationError({'iso3': 'No any iso3 found for the country'})
        return data

    def create(self, validated_data):
        iso3 = validated_data.pop('country_iso3', None)
        validated_data['country'] = Country.objects.filter(iso3=iso3).first()
        return ParkedItem.objects.create(**validated_data)


class ParkedItemUpdateSerializer(UpdateSerializerMixin, ParkedItemSerializer):
    id = IntegerIDField(required=True)
