from collections import OrderedDict

from django.db.models import Min, Max
from django.utils.translation import gettext
from rest_framework import serializers

from apps.crisis.models import Crisis
from apps.contrib.serializers import UpdateSerializerMixin, IntegerIDField


class CrisisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crisis
        fields = '__all__'

    def validate_dates(self, attrs):
        errors = OrderedDict()

        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = attrs.get('end_date', getattr(self.instance, 'end_date', None))

        if start_date and end_date and end_date < start_date:
            errors['start_date'] = 'Start date should be smaller than end date.'

        return errors

    def validate_event_dates(self, attrs):
        errors = OrderedDict()
        if not self.instance:
            return errors

        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = attrs.get('end_date', getattr(self.instance, 'end_date', None))

        min_event_start_date = self.instance.events.aggregate(
            _date=Min('start_date')
        )['_date']
        max_event_start_date = self.instance.events.aggregate(
            _date=Max('start_date')
        )['_date']
        min_event_end_date = self.instance.events.aggregate(
            _date=Min('end_date')
        )['_date']
        max_event_end_date = self.instance.events.aggregate(
            _date=Max('end_date')
        )['_date']

        if start_date:
            if (
                (max_event_start_date and not start_date <= max_event_start_date) or
                (min_event_start_date and not start_date <= min_event_start_date)
            ):
                errors['start_date'] = gettext('Start date of one of the events is out of range.')
        if end_date:
            if (
                (max_event_end_date and not end_date >= max_event_end_date) or
                (min_event_end_date and not end_date >= min_event_end_date)
            ):
                errors['end_date'] = gettext('End date of one of the events is out of range.')
        return errors

    def validate_event_countries(self, attrs):
        errors = OrderedDict()
        if not self.instance:
            return errors

        countries = attrs.get('countries')
        if countries is None:
            return errors
        event_countries = self.instance.events.filter(countries__isnull=False).values_list('countries', flat=True)

        if not event_countries:
            return errors
        if set(event_countries).difference(countries):
            errors['countries'] = gettext(
                'The included events have more countries than mentioned in this crisis.'
            )
        return errors

    def validate_event_types(self, attrs):
        errors = OrderedDict()
        if not self.instance:
            return errors
        crisis_type = attrs.get('crisis_type')
        if crisis_type is None:
            return errors
        if not self.instance.events.exists():
            return errors
        # all events are bound to be the same as crisis type
        event_type = self.instance.events.first().event_type.value
        if event_type and crisis_type != event_type:
            errors['crisis_type'] = gettext(
                'There are events with different crisis types'
            )
        return errors

    def validate(self, attrs):
        errors = OrderedDict()
        errors.update(self.validate_dates(attrs))
        if self.instance:
            errors.update(self.validate_event_dates(attrs))
            errors.update(self.validate_event_countries(attrs))
            errors.update(self.validate_event_types(attrs))
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def udpate(self, *a, **kw):
        raise NotImplementedError('Use `CrisisUpdateSerializer` instead')


class CrisisUpdateSerializer(UpdateSerializerMixin, CrisisSerializer):
    """Created simply to generate the input type for mutations"""
    id = IntegerIDField(required=True)
