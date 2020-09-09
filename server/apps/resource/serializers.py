from rest_framework import serializers

from apps.resource.models import Resource, ResourceGroup

from apps.contrib.serializers import MetaInformationSerializerMixin


class ResourceSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = '__all__'


class ResourceGroupSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ResourceGroup
        fields = '__all__'
