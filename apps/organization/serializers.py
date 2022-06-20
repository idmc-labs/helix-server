from rest_framework import serializers

from apps.organization.models import Organization, OrganizationKind
from apps.contrib.serializers import UpdateSerializerMixin, IntegerIDField, MetaInformationSerializerMixin


class OrganizationKindSerializer(serializers.ModelSerializer, MetaInformationSerializerMixin):
    class Meta:
        model = OrganizationKind
        fields = '__all__'


class OrganizationKindUpdateSerializer(UpdateSerializerMixin, OrganizationKindSerializer):
    id = IntegerIDField(required=True)


class OrganizationSerializer(serializers.ModelSerializer, MetaInformationSerializerMixin):
    class Meta:
        model = Organization
        fields = '__all__'
        extra_kwargs = {
            'countries': {
                'required': False
            },
        }


class OrganizationUpdateSerializer(UpdateSerializerMixin, OrganizationSerializer, MetaInformationSerializerMixin):
    id = IntegerIDField(required=True)
