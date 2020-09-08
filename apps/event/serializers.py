from collections import OrderedDict

from django.core.exceptions import ValidationError
from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.event.models import Event


class EventSerializer(MetaInformationSerializerMixin,
                      serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'

    def validate(self, attrs: dict) -> None:
        errors = OrderedDict()
        errors.update(Event.clean_dates(attrs, self.instance))
        errors.update(Event.clean_by_event_type(attrs, self.instance))
        if errors:
            raise ValidationError(errors)
        return attrs
