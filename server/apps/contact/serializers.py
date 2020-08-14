from rest_framework import serializers

from apps.contact.models import Contact, Communication


class CommunicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Communication
        fields = ['id', 'contact', 'country', 'subject', 'content', 'date', 'medium']


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'designation', 'name', 'country', 'job_title']
