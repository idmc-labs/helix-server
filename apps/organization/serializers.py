from rest_framework import serializers

from apps.organization.models import Organization, OrganizationKind
from apps.contrib.serializers import UpdateSerializerMixin, IntegerIDField


class OrganizationKindSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationKind
        fields = '__all__'


class OrganizationKindUpdateSerializer(UpdateSerializerMixin, OrganizationKindSerializer):
    id = IntegerIDField(required=True)


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'
        extra_kwargs = {
            'countries': {
                'required': False
            },
        }


class OrganizationUpdateSerializer(UpdateSerializerMixin, OrganizationSerializer):
    id = IntegerIDField(required=True)
