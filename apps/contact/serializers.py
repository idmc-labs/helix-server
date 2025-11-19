from rest_framework import serializers

from apps.contact.models import Communication, Contact
from apps.contrib.serializers import IntegerIDField, MetaInformationSerializerMixin, UpdateSerializerMixin


class CommunicationSerializer(serializers.ModelSerializer, MetaInformationSerializerMixin):
    class Meta:
        model = Communication
        fields = "__all__"

    def validate_document(self, document) -> dict:
        if document and not document.is_file_uploaded:
            return serializers.ValidationError("Document must be uploaded before linking to communication.")
        return document


class CommunicationUpdateSerializer(UpdateSerializerMixin, CommunicationSerializer):
    id = IntegerIDField(required=True)


class ContactSerializer(serializers.ModelSerializer, MetaInformationSerializerMixin):
    class Meta:
        model = Contact
        fields = "__all__"


class ContactUpdateSerializer(UpdateSerializerMixin, ContactSerializer):
    id = IntegerIDField(required=True)
