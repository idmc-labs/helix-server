from rest_framework import serializers

from apps.contact.models import Communication, Contact
from apps.contrib.serializers import IntegerIDField, MetaInformationSerializerMixin, UpdateSerializerMixin


class CommunicationSerializer(serializers.ModelSerializer, MetaInformationSerializerMixin):
    class Meta:
        model = Communication
        fields = "__all__"


class CommunicationUpdateSerializer(UpdateSerializerMixin, CommunicationSerializer):
    id = IntegerIDField(required=True)


class ContactSerializer(serializers.ModelSerializer, MetaInformationSerializerMixin):
    class Meta:
        model = Contact
        fields = "__all__"


class ContactUpdateSerializer(UpdateSerializerMixin, ContactSerializer):
    id = IntegerIDField(required=True)
