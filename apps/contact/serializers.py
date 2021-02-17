from rest_framework import serializers

from apps.contact.models import Contact, Communication


class CommunicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Communication
        fields = '__all__'


class ContactWithoutOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        exclude = ['organization']


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'
