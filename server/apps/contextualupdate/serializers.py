from collections import OrderedDict

from django.utils.translation import gettext
from rest_framework import serializers

from apps.contextualupdate.models import ContextualUpdate
from apps.contrib.serializers import MetaInformationSerializerMixin


class ContextualUpdateSerializer(MetaInformationSerializerMixin,
                                 serializers.ModelSerializer):
    class Meta:
        model = ContextualUpdate
        fields = '__all__'

    def validate_url_document(self, attrs):
        errors = OrderedDict()
        if not self.instance:
            if not attrs.get('url') and not attrs.get('document'):
                errors['url'] = gettext('Please fill the URL or upload a document. ')
                errors['document'] = gettext('Please fill the URL or upload a document. ')
            raise serializers.ValidationError(errors)

    def validate(self, attrs) -> dict:
        self.validate_url_document(attrs)
        return attrs
