from rest_framework import serializers

from apps.contact.models import Contact, Communication
from apps.contrib.serializers import UpdateSerializerMixin, IntegerIDField, MetaInformationSerializerMixin


class CommunicationSerializer(serializers.ModelSerializer, MetaInformationSerializerMixin):
    class Meta:
        model = Communication
        fields = '__all__'


class CommunicationUpdateSerializer(UpdateSerializerMixin, CommunicationSerializer):
    id = IntegerIDField(required=True)


class ContactSerializer(serializers.ModelSerializer, MetaInformationSerializerMixin):
    class Meta:
        model = Contact
        fields = '__all__'


class ContactUpdateSerializer(UpdateSerializerMixin, ContactSerializer):
    id = IntegerIDField(required=True)
