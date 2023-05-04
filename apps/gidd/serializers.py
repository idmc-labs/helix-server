from rest_framework import serializers
from apps.country.models import Country
from .models import (
    Conflict, Disaster, StatusLog, ReleaseMetadata,
    DisplacementData,
)


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'
        lookup_field = 'id'


class ConflictSerializer(serializers.ModelSerializer):
    country = CountrySerializer()

    class Meta:
        model = Conflict
        fields = '__all__'
        lookup_field = 'id'


class DisasterSerializer(serializers.ModelSerializer):
    country = CountrySerializer()

    class Meta:
        model = Disaster
        fields = '__all__'
        lookup_field = 'id'


class StatusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusLog
        fields = '__all__'


class ReleaseMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReleaseMetadata
        fields = ('pre_release_year', 'release_year')

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['modified_by'] = user
        return ReleaseMetadata.objects.create(**validated_data)


class DisplacementDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisplacementData
        fields = '__all__'
