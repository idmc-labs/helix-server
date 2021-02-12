from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.parking_lot.models import ParkedItem


class ParkedItemSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ParkedItem
        fields = '__all__'
