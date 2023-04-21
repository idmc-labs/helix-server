from rest_framework import serializers
from apps.country.models import Country
from .models import Conflict, Disaster, GiddLog, ReleaseMetadata


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'
        lookup_field = 'id'


class ConflictSerializer(serializers.ModelSerializer):
    country = CountrySerializer(many=False)

    class Meta:
        model = Conflict
        fields = '__all__'
        lookup_field = 'id'


class DisasterSerializer(serializers.ModelSerializer):
    country = CountrySerializer(many=False)

    class Meta:
        model = Disaster
        fields = '__all__'
        lookup_field = 'id'


class GiddLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiddLog
        fields = '__all__'


class ReleaseMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReleaseMetadata
        fields = ('staging_year', 'production_year')

    def create(self, validated_data):
        # Always update a object instead of create
        meta_data = ReleaseMetadata.objects.first()
        user = self.context['request'].user
        if not meta_data:
            return ReleaseMetadata.objects.create(
                production_year=validated_data.get('production_year'),
                staging_year=validated_data.get('staging_year'),
                modified_by=user
            )
        else:
            meta_data.production_year = validated_data.get('production_year')
            meta_data.staging_year = validated_data.get('staging_year')
            meta_data.modified_by = user
            return meta_data
