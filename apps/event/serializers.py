from collections import OrderedDict

from django.core.exceptions import ValidationError
from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin, UpdateSerializerMixin
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
    id = serializers.IntegerField(required=True)


class EventSerializer(MetaInformationSerializerMixin,
                      serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'

    def validate(self, attrs: dict) -> dict:
        errors = OrderedDict()
        errors.update(Event.clean_dates(attrs, self.instance))
        errors.update(Event.clean_by_event_type(attrs, self.instance))
        errors.update(
            is_child_parent_inclusion_valid(attrs, self.instance, field='countries', parent_field='crisis.countries')
        )
        if errors:
            raise ValidationError(errors)
        if attrs.get('event_type',
                     getattr(self.instance, 'event_type', None)
                     ) is not Crisis.CRISIS_TYPE.OTHER.value:
            # only let following field if the event type is other
            attrs['other_sub_type'] = None
        return attrs


class EventUpdateSerializer(UpdateSerializerMixin, EventSerializer):
    id = serializers.IntegerField(required=True)