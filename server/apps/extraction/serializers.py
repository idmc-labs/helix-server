from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin
from .models import ExtractionQuery


class ExtractionQuerySerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ExtractionQuery
        fields = '__all__'
