from django.db import transaction
from rest_framework import serializers

from apps.contact.models import Contact
from apps.contact.serializers import ContactWithoutOrganizationSerializer
from apps.organization.models import Organization, OrganizationKind


class OrganizationKindSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationKind
        fields = ['id', 'title']

    def validate_title(self, value):
        raise serializers.ValidationError('blaaa title')


class OrganizationSerializer(serializers.ModelSerializer):
    contacts = ContactWithoutOrganizationSerializer(many=True)
    organization_kind = OrganizationKindSerializer()

    class Meta:
        model = Organization
        fields = ['id', 'short_name', 'title', 'methodology', 'organization_kind',
                  'source_detail_methodology', 'parent', 'contacts']

    def validate_title(self, value):
        raise serializers.ValidationError('blaa org title')

    def create(self, validated_data):
        contacts = validated_data.pop('contacts', [])
        organization_kind = validated_data.pop('organization_kind', {})
        if contacts:
            with transaction.atomic():
                organization_kind = OrganizationKind.objects.create(**organization_kind)
                organization = Organization.objects.create(**validated_data, organization_kind=organization_kind)
                Contact.objects.bulk_create([Contact(**each, organization=organization) for each in contacts])
        else:
            organization = Organization.objects.create(**validated_data)
        return organization
