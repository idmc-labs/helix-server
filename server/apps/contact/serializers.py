from django.db import transaction
from rest_framework import serializers

from apps.contact.models import Contact, Communication


class CommunicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Communication
        fields = '__all__'

    def validate_content(self, value):
        raise serializers.ValidationError('Comm ko error.')


class CommunicationNestedSerializer(serializers.ModelSerializer):
    contact = serializers.IntegerField(required=False)

    class Meta:
        model = Communication
        fields = '__all__'

    def validate_content(self, value):
        raise serializers.ValidationError('Comm ko error.')


class ContactSerializer(serializers.ModelSerializer):
    communications = CommunicationSerializer(many=True)

    class Meta:
        model = Contact
        fields = ['id', 'designation', 'name', 'country', 'organization', 'job_title',
                  'communications']

    def create(self, validated_data):
        communications = validated_data.pop('communications')
        with transaction.atomic():
            contact = Contact.objects.create(**validated_data)
            communications = [Communication(**each, contact=contact) for each in communications]
            Communication.objects.bulk_create(communications)
        return contact
