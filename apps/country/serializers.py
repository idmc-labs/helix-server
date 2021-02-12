from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.country.models import Summary, ContextualAnalysis


class SummarySerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Summary
        fields = '__all__'


class ContextualAnalysisSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ContextualAnalysis
        fields = '__all__'
