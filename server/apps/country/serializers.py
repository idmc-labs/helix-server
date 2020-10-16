from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.country.models import Summary, ContextualUpdate


class SummarySerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Summary
        fields = '__all__'


class ContextualUpdateSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ContextualUpdate
        fields = '__all__'
