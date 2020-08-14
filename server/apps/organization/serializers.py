from django.db import transaction
from rest_framework import serializers

from apps.contact.models import Contact
from apps.contact.serializers import ContactSerializer
from apps.organization.models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(many=True)

    class Meta:
        model = Organization
        fields = ['title', 'methodology', 'source_detail_methodology', 'parent',
                  'contacts']

    def create(self, validated_data):
        with transaction.atomic():
            contacts = validated_data.pop('contacts', [])
            organization = Organization.objects.create(**validated_data)
            Contact.objects.bulk_create([Contact(**each, organization=organization) for each in contacts])
        return organization
