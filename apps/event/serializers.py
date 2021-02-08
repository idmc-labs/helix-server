from collections import OrderedDict

from django.core.exceptions import ValidationError
from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.crisis.models import Crisis
from apps.event.models import Event, Actor


class ActorSerializer(MetaInformationSerializerMixin,
                      serializers.ModelSerializer):
    class Meta:
        model = Actor
        fields = '__all__'


class EventSerializer(MetaInformationSerializerMixin,
                      serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'

    def validate_within_crisis_countries(self, attrs: dict):
        errors = OrderedDict()
        if not attrs.get('crisis') or not attrs.get('countries'):
            return errors
        if set(attrs['countries']).difference(attrs['crisis'].countries.all()):
            errors.update({
                'countries': 'Outside countries of crisis'
            })
        return errors

    def validate(self, attrs: dict) -> dict:
        errors = OrderedDict()
        errors.update(Event.clean_dates(attrs, self.instance))
        errors.update(Event.clean_by_event_type(attrs, self.instance))
        errors.update(self.validate_within_crisis_countries(attrs))
        if errors:
            raise ValidationError(errors)
        if attrs.get('event_type',
                     getattr(self.instance, 'event_type', None)
                     ) is not Crisis.CRISIS_TYPE.OTHER.value:
            # only let following field if the event type is other
            attrs['other_sub_type'] = None
        return attrs
