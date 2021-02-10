from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin, UpdateSerializerMixin
from apps.parking_lot.models import ParkedItem


class ParkedItemSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ParkedItem
        fields = '__all__'


class ParkedItemUpdateSerializer(UpdateSerializerMixin, ParkedItemSerializer):
    id = serializers.IntegerField(required=True)