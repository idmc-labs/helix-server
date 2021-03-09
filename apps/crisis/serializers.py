from rest_framework import serializers

from apps.crisis.models import Crisis
from apps.contrib.serializers import UpdateSerializerMixin, IntegerIDField


class CrisisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crisis
        fields = '__all__'


class CrisisUpdateSerializer(UpdateSerializerMixin, CrisisSerializer):
    """Created simply to generate the input type for mutations"""
    id = IntegerIDField(required=True)
