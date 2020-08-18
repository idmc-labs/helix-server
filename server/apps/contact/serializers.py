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

    def validate_first_name(self, value):
        import random
        if random.choice([1, 0]):
            raise serializers.ValidationError('blaaa first_name')
        return value


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'
