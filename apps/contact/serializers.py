from rest_framework import serializers

from apps.contact.models import Contact, Communication


class CommonCommunicationValidatorMixin(object):
    pass


class CommonContactValidatorMixin(object):
    pass


class CommunicationSerializer(CommonCommunicationValidatorMixin,
                              serializers.ModelSerializer):
    class Meta:
        model = Communication
        fields = '__all__'


class ContactWithoutOrganizationSerializer(CommonContactValidatorMixin,
                                           serializers.ModelSerializer):
    class Meta:
        model = Contact
        exclude = ['organization']


class ContactSerializer(CommonContactValidatorMixin,
                        serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'
