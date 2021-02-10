from rest_framework import serializers

from apps.contact.models import Contact, Communication
from apps.contrib.serializers import UpdateSerializerMixin


class CommunicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Communication
        fields = '__all__'


class CommunicationUpdateSerializer(UpdateSerializerMixin, CommunicationSerializer):
    id = serializers.IntegerField(required=True)


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'


class ContactUpdateSerializer(UpdateSerializerMixin, ContactSerializer):
    id = serializers.IntegerField(required=True)
