from rest_framework import serializers
from apps.country.models import Country
from .models import Conflict, Disaster, StatusLog, ReleaseMetadata


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
        fields = ('staging_year', 'production_year')

    def create(self, validated_data):
        # Always update a object instead of create
        user = self.context['request'].user
        meta_data = ReleaseMetadata.objects.first() or ReleaseMetadata()
        meta_data.production_year = validated_data.get('production_year')
        meta_data.staging_year = validated_data.get('staging_year')
        meta_data.modified_by = user
        meta_data.save()
        return meta_data