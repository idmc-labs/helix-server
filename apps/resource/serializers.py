from django.utils.translation import gettext
from rest_framework import serializers

from helix.settings import RESOURCE_NUMBER, RESOURCEGROUP_NUMBER

from apps.resource.models import Resource, ResourceGroup

from apps.contrib.serializers import MetaInformationSerializerMixin, UpdateSerializerMixin


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
            raise serializers.ValidationError(gettext(f"Can only create {RESOURCE_NUMBER} resources"))
        return super().validate(attrs)


class ResourceUpdateSerializer(UpdateSerializerMixin, ResourceSerializer):
    id = serializers.IntegerField(required=True)


class ResourceGroupSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ResourceGroup
        fields = '__all__'

    def validate(self, attrs) -> dict:
        if self.instance is None and ResourceGroup.objects.filter(
            created_by=self.context['request'].user
        ).count() >= RESOURCEGROUP_NUMBER:
            raise serializers.ValidationError(gettext(f"Can only create {RESOURCEGROUP_NUMBER} resource groups"))
        return super().validate(attrs)


class ResourceGroupUpdateSerializer(UpdateSerializerMixin, ResourceGroupSerializer):
    id = serializers.IntegerField(required=True)