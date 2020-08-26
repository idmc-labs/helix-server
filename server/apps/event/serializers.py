from rest_framework import serializers

from apps.event.models import Event


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'

    def validate(self, attrs):
        countries = attrs.pop('countries', [])
        instance = Event(**attrs)
        instance.clean()
        attrs.update(dict(countries=countries))
        return attrs
