from rest_framework import serializers

from .models import ExtractionQuery


class ExtractionQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractionQuery
        fields = '__all__'
