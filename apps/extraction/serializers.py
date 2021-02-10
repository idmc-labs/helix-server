from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin, UpdateSerializerMixin
from .models import ExtractionQuery


class ExtractionQuerySerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ExtractionQuery
        fields = '__all__'


class ExtractionQueryUpdateSerializer(UpdateSerializerMixin, ExtractionQuerySerializer):
    id = serializers.IntegerField(required=True)