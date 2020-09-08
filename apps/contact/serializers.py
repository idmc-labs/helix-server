from rest_framework import serializers

from apps.contact.models import Contact, Communication


class CommonCommunicationValidatorMixin(object):
    pass


class CommonContactValidatorMixin(object):
    def validate_phone(self, phone):
        if Contact.objects.exclude(phone=None).filter(phone=phone).exists():
            raise serializers.ValidationError('Phone Number already exists.')
        return phone


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
