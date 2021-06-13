from collections import OrderedDict

from django.core.exceptions import ValidationError
from django.db.models import Min, Max, Q
from django.utils.translation import gettext
from rest_framework import serializers

from apps.contrib.serializers import (
    MetaInformationSerializerMixin,
    UpdateSerializerMixin,
    IntegerIDField,
)
from apps.country.models import Country
from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.entry.constants import FLOW
from apps.event.models import Event, Actor
from utils.validations import is_child_parent_inclusion_valid, is_child_parent_dates_valid


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

    def validate_violence_sub_type_and_type(self, attrs):
        errors = OrderedDict()
        _type = attrs.get('violence', getattr(self.instance, 'violence', None))
        sub_type = attrs.get(
            'violence_sub_type',
            getattr(self.instance, 'violence_sub_type', None)
        )
        if sub_type and sub_type.violence != _type:
            errors['violence_sub_type'] = gettext('Violence sub-type does not match the violence type.')
        return errors

    def validate_event_type_with_crisis_type(self, attrs):
        errors = OrderedDict()
        crisis = attrs.get(
            'crisis',
            getattr(self.instance, 'crisis', None)
        )
        event_type = attrs.get(
            'event_type',
            getattr(self.instance, 'event_type', None)
        )
        if crisis and crisis.crisis_type != event_type:
            errors['event_type'] = gettext('Event type does not match the crisis type.')
        return errors

    def validate_disaster_disaster_sub_type(self, attrs):
        errors = OrderedDict()
        if not attrs.get(
            'disaster_sub_type',
            getattr(self.instance, 'disaster_sub_type', None)
        ):
            errors['disaster_sub_type'] = gettext('Please mention the sub-type of disaster.')
        return errors

    def validate_event_type_against_crisis_type(self, event_type, attrs):
        crisis = attrs.get('crisis', getattr(self.instance, 'crisis', None))
        if crisis and event_type != crisis.crisis_type.value:
            raise serializers.ValidationError({'event_type': gettext('Event type and crisis type do not match.')})

    def validate_figures_countries(self, attrs):
        '''
        downward validation by considering children during event update
        '''
        errors = OrderedDict()
        if not self.instance:
            return errors

        countries = [each.id for each in attrs.get('countries', [])]
        if not countries:
            return errors
        figures_countries = Figure.objects.filter(
            country__isnull=False,
            entry__event=self.instance
        ).values_list('country', flat=True)
        if diffs := set(figures_countries).difference(countries):
            errors['countries'] = gettext(
                'The included figures have following countries not mentioned in the event: %s'
            ) % ', '.join([item for item in Country.objects.filter(id__in=diffs).values_list('name', flat=True)])

        return errors

    def validate_figures_dates(self, attrs):
        errors = OrderedDict()
        if not self.instance:
            return errors

        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = attrs.get('end_date', getattr(self.instance, 'end_date', None))

        _ = Figure.objects.filter(
            entry__event=self.instance,
        ).aggregate(
            min_date=Min(
                'start_date',
                filter=Q(
                    start_date__isnull=False,
                )
            ),
            max_date=Max(
                'end_date',
                filter=Q(
                    end_date__isnull=False,
                    category__type=FLOW
                )
            ),
        )
        min_start_date = _['min_date']
        max_end_date = _['max_date']

        if start_date and (min_start_date and min_start_date < start_date):
            errors['start_date'] = gettext('Earliest start date of one of the figures is %s.') % min_start_date
        if end_date and (max_end_date and max_end_date > end_date):
            errors['end_date'] = gettext('Farthest end date of one of the figures is %s.') % max_end_date
        return errors

    def validate_empty_countries(self, attrs):
        errors = OrderedDict()
        countries = attrs.get('countries')
        if not countries and not (self.instance and self.instance.countries.exists()):
            errors.update(dict(
                countries=gettext('This field is required.')
            ))
        return errors

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        errors = OrderedDict()
        crisis = attrs.get('crisis') or getattr(self.instance, 'crisis', None)
        if crisis:
            errors.update(is_child_parent_dates_valid(
                attrs.get('start_date', getattr(self.instance, 'start_date', None)),
                attrs.get('end_date', getattr(self.instance, 'end_date', None)),
                crisis.start_date,
                crisis.end_date,
            ))
            errors.update(
                is_child_parent_inclusion_valid(attrs, self.instance, field='countries', parent_field='crisis.countries')
            )
        errors.update(self.validate_event_type_with_crisis_type(attrs))
        if attrs.get('event_type') == Crisis.CRISIS_TYPE.DISASTER:
            errors.update(self.validate_disaster_disaster_sub_type(attrs))
        if attrs.get('event_type') == Crisis.CRISIS_TYPE.CONFLICT:
            errors.update(self.validate_violence_sub_type_and_type(attrs))

        if self.instance:
            errors.update(self.validate_figures_countries(attrs))
            errors.update(self.validate_figures_dates(attrs))

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
