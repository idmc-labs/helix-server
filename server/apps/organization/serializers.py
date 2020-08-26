from django.db import transaction
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from apps.contact.models import Contact
from apps.contact.serializers import ContactWithoutOrganizationSerializer
from apps.organization.models import Organization, OrganizationKind


class OrganizationKindSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationKind
        fields = '__all__'


class OrganizationSerializer(serializers.ModelSerializer):
    contacts = ContactWithoutOrganizationSerializer(many=True)

    class Meta:
        model = Organization
        fields = '__all__'

    def validate_contacts(self, contacts):
        phone_numbers = [phone for contact in contacts if (phone := contact['phone']) is not None]
        if len(phone_numbers) != len(set(phone_numbers)):
            raise serializers.ValidationError(_('Contacts you entered have duplicate phone numbers.'))
        return contacts

    def create(self, validated_data):
        contacts = validated_data.pop('contacts', [])
        if contacts:
            with transaction.atomic():
                organization = Organization.objects.create(**validated_data)
                Contact.objects.bulk_create([
                    Contact(**each, organization=organization) for each in contacts
                ])
        else:
            organization = Organization.objects.create(**validated_data)
        return organization
