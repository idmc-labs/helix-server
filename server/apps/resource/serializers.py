from django.utils.translation import gettext
from rest_framework import serializers

from apps.resource.models import Resource, ResourceGroup

from apps.contrib.serializers import MetaInformationSerializerMixin


class ResourceSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = '__all__'

    def validate_group(self, group):
        if group and group.created_by != self.context['request'].user:
            raise serializers.ValidationError(gettext('Group does not exist.'))
        return group


class ResourceGroupSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ResourceGroup
        fields = '__all__'
