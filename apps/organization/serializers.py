from rest_framework import serializers
from django.utils.translation import gettext

from apps.organization.models import Organization, OrganizationKind
from apps.contrib.serializers import UpdateSerializerMixin


class OrganizationKindSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationKind
        fields = '__all__'


class OrganizationKindUpdateSerializer(UpdateSerializerMixin, OrganizationKindSerializer):
    id = serializers.IntegerField(required=True)


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'


class OrganizationUpdateSerializer(UpdateSerializerMixin, OrganizationSerializer):
    id = serializers.IntegerField(required=True)