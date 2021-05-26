from django.utils.translation import gettext
from rest_framework import serializers

from helix.settings import RESOURCE_NUMBER, RESOURCEGROUP_NUMBER

from apps.resource.models import Resource, ResourceGroup

from apps.contrib.serializers import (
    MetaInformationSerializerMixin,
    UpdateSerializerMixin,
    IntegerIDField,
)


class ResourceSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = '__all__'

    def validate_group(self, group):
        if group and group.created_by != self.context['request'].user:
            raise serializers.ValidationError(gettext('Group does not exist.'))
        return group

    def validate(self, attrs) -> dict:
        if self.instance is None and Resource.objects.filter(
            created_by=self.context['request'].user
        ).count() >= RESOURCE_NUMBER:
            raise serializers.ValidationError(gettext('Can only create %s resources') % RESOURCE_NUMBER)
        return super().validate(attrs)


class ResourceUpdateSerializer(UpdateSerializerMixin, ResourceSerializer):
    id = IntegerIDField(required=True)


class ResourceGroupSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ResourceGroup
        fields = '__all__'

    def validate(self, attrs) -> dict:
        if self.instance is None and ResourceGroup.objects.filter(
            created_by=self.context['request'].user
        ).count() >= RESOURCEGROUP_NUMBER:
            raise serializers.ValidationError(gettext('Can only create %s resource groups') % RESOURCEGROUP_NUMBER)
        return super().validate(attrs)


class ResourceGroupUpdateSerializer(UpdateSerializerMixin, ResourceGroupSerializer):
    id = IntegerIDField(required=True)
