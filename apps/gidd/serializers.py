from rest_framework import serializers
from apps.country.models import Country
from .models import Conflict, Disaster


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
