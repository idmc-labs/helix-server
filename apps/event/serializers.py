from collections import OrderedDict

from django.core.exceptions import ValidationError
from django.utils.translation import gettext
from rest_framework import serializers

from apps.contrib.serializers import (
    MetaInformationSerializerMixin,
    UpdateSerializerMixin,
    IntegerIDField,
)
from apps.crisis.models import Crisis
from apps.event.models import Event, Actor
from utils.validations import is_child_parent_inclusion_valid


class ActorSerializer(MetaInformationSerializerMixin,
                      serializers.ModelSerializer):
    class Meta:
        model = Actor
        fields = '__all__'


class ActorUpdateSerializer(UpdateSerializerMixin,
                            ActorSerializer):
    """Just to create input type"""
    id = IntegerIDField(required=True)


class EventSerializer(MetaInformationSerializerMixin,
                      serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'

    def validate_event_type_against_crisis_type(self, event_type, attrs):
        crisis = attrs.get('crisis', getattr(self.instance, 'crisis', None))
        if crisis and event_type != crisis.crisis_type.value:
            raise serializers.ValidationError({'event_type': gettext('Event type and crisis type do not match.')})

    def validate(self, attrs: dict) -> dict:
        errors = OrderedDict()
        errors.update(Event.clean_by_event_type(attrs, self.instance))
        if attrs.get('crisis') or getattr(self.instance, 'crisis', None):
            errors.update(Event.clean_dates(attrs, self.instance))
            errors.update(
                is_child_parent_inclusion_valid(attrs, self.instance, field='countries', parent_field='crisis.countries')
            )
        if errors:
            raise ValidationError(errors)

        # only set other_sub_type if event_type is not OTHER
        event_type = attrs.get('event_type', getattr(self.instance, 'event_type', None))
        if event_type != Crisis.CRISIS_TYPE.OTHER.value:
            attrs['other_sub_type'] = None

        self.validate_event_type_against_crisis_type(event_type, attrs)

        return attrs


class EventUpdateSerializer(UpdateSerializerMixin, EventSerializer):
    id = IntegerIDField(required=True)
