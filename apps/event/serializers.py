import typing
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
from apps.event.models import Event, Actor, ContextOfViolence, EventCode
from utils.validations import is_child_parent_inclusion_valid, is_child_parent_dates_valid
from apps.notification.models import Notification


class ActorSerializer(MetaInformationSerializerMixin,
                      serializers.ModelSerializer):
    class Meta:
        model = Actor
        fields = '__all__'


class ActorUpdateSerializer(UpdateSerializerMixin,
                            ActorSerializer):
    """Just to create input type"""
    id = IntegerIDField(required=True)


class EventCodeSerializer(MetaInformationSerializerMixin,
                          serializers.ModelSerializer):

    class Meta:
        model = EventCode
        fields = ['country', 'uuid', 'event_code', 'event_code_type']
        extra_kwargs = {
            'uuid': {
                'validators': [],
                'required': True
            },
        }


class EventCodeUpdateSerializer(serializers.ModelSerializer):
    id = IntegerIDField(required=False)

    class Meta:
        model = EventCode
        exclude = ['event']
        extra_kwargs = {
            'uuid': {
                'validators': [],
                'required': True
            },
        }


class EventSerializer(MetaInformationSerializerMixin,
                      serializers.ModelSerializer):

    event_codes = EventCodeSerializer(many=True, required=False)

    class Meta:
        model = Event
        exclude = (
            'assigner',
            'assigned_at',
            'review_status',
            'glide_numbers',
            'assignee',
            'disaster_category',
            'disaster_type',
            'ignore_qa',
            'old_id',
            'version_id',
            'violence',
        )

    def validate_violence_sub_type_and_type(self, attrs):
        errors = OrderedDict()
        if not attrs.get(
            'violence_sub_type',
            getattr(self.instance, 'violence_sub_type', None)
        ):
            errors['violence_sub_type'] = gettext('Please mention the sub type of violence.')
        return errors

    def validate_event_type_with_crisis_type(self, attrs):
        errors = OrderedDict()
        crisis = attrs.get('crisis')
        event_type = attrs.get(
            'event_type',
            getattr(self.instance, 'event_type', None)
        )
        if crisis and crisis.crisis_type != event_type:
            errors['event_type'] = (
                gettext('Event cause should be {} to match the crisis cause').format(
                    gettext(crisis.crisis_type.label.lower())
                )
            )
        return errors

    def validate_disaster_disaster_sub_type(self, attrs):
        errors = OrderedDict()
        if not attrs.get(
            'disaster_sub_type',
            getattr(self.instance, 'disaster_sub_type', None)
        ):
            errors['disaster_sub_type'] = gettext('Please mention the sub type of disaster.')
        return errors

    def validate_event_type_against_crisis_type(self, event_type, attrs):
        crisis = attrs.get('crisis')
        if crisis and event_type != crisis.crisis_type.value:
            raise serializers.ValidationError({'event_type': gettext('Event cause and crisis cause do not match.')})

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
            event=self.instance
        ).values_list('country', flat=True)
        if diffs := set(figures_countries).difference(countries):
            errors['countries'] = gettext(
                'The included figures have following countries not mentioned in the event: %s'
            ) % ', '.join([item for item in Country.objects.filter(id__in=diffs).values_list('idmc_short_name', flat=True)])

        return errors

    def validate_figures_dates(self, attrs):
        errors = OrderedDict()
        if not self.instance:
            return errors

        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))

        _ = Figure.objects.filter(
            event=self.instance,
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
                    category__in=Figure.flow_list()
                )
            ),
        )
        min_start_date = _['min_date']
        if start_date and (min_start_date and min_start_date < start_date):
            errors['start_date'] = gettext('Earliest start date of one of the figures is %s.') % min_start_date
        return errors

    def validate_empty_countries(self, attrs):
        errors = OrderedDict()
        countries = attrs.get('countries')
        if not countries and not (self.instance and self.instance.countries.exists()):
            errors.update(dict(
                countries=gettext('This field is required.')
            ))
        return errors

    def _update_event_codes(self, event: Event, event_codes: typing.List[typing.Dict]):
        instance_event_codes_qs = EventCode.objects.filter(event=event)

        # For empty - Delete all
        if not event_codes:
            instance_event_codes_qs.delete()
            return

        # Delete missing event_codes
        event_code_to_delete_qs = instance_event_codes_qs.exclude(
            id__in=[
                each['id']
                for each in event_codes
                if each.get('id')
            ]
        )
        event_code_to_delete_qs.delete()

        # Update provided event_codes
        for code in event_codes:
            if not code.get('id'):
                # Create new
                event_code_ser = EventCodeSerializer(context=self.context)
            else:
                # Update existing
                event_code_ser = EventCodeUpdateSerializer(
                    instance=instance_event_codes_qs.get(id=code['id']),
                    partial=True,
                    context=self.context,
                )
            event_code_ser._validated_data = {**code, 'event': event}
            event_code_ser._errors = {}
            event_code_ser.save()

    def _update_parent_fields(self, attrs):
        disaster_sub_type = attrs.get('disaster_sub_type', self.instance and self.instance.disaster_sub_type)
        violence_sub_type = attrs.get('violence_sub_type', self.instance and self.instance.violence_sub_type)

        attrs['disaster_category'] = None
        attrs['disaster_type'] = None
        attrs['disaster_sub_category'] = None
        attrs['violence'] = None

        if disaster_sub_type:
            disaster_type = disaster_sub_type.type
            attrs['disaster_type'] = disaster_type
            if disaster_type:
                disaster_sub_category = disaster_type.disaster_sub_category
                attrs['disaster_sub_category'] = disaster_sub_category
                if disaster_sub_category:
                    attrs['disaster_category'] = disaster_sub_category.category

        if violence_sub_type:
            attrs['violence'] = violence_sub_type.violence

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        self._update_parent_fields(attrs)
        errors = OrderedDict()
        crisis = attrs.get('crisis')
        if crisis:
            errors.update(is_child_parent_dates_valid(
                attrs.get('start_date', getattr(self.instance, 'start_date', None)),
                attrs.get('end_date', getattr(self.instance, 'end_date', None)),
                crisis.start_date,
                'crisis',
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

        for attr in ['event_narrative']:
            if not attrs.get(attr, None):
                errors.update({attr: gettext('This field is required.')})

        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context['request'].user
        countries = validated_data.pop("countries", None)
        context_of_violence = validated_data.pop("context_of_violence", None)
        event_codes = validated_data.pop("event_codes", None)
        event = Event.objects.create(**validated_data)
        if countries:
            event.countries.set(countries)
        if context_of_violence:
            event.context_of_violence.set(context_of_violence)

        if event_codes:
            for event_code in event_codes:
                EventCode.objects.create(
                    event=event,
                    country=event_code.get("country"),
                    event_code=event_code.get("event_code"),
                    event_code_type=event_code.get("event_code_type"),
                )
        context_of_violence = validated_data.pop("context_of_violence", None)
        return event

    def update(self, instance, validated_data):
        # Update event status if include_triangulation_in_qa is changed
        validated_data['last_modified_by'] = self.context['request'].user

        is_include_triangulation_in_qa_changed = False
        if 'include_triangulation_in_qa' in validated_data:
            new_include_triangulation_in_qa = validated_data.get('include_triangulation_in_qa')
            is_include_triangulation_in_qa_changed = new_include_triangulation_in_qa != instance.include_triangulation_in_qa

        # Update Event Codes
        if "event_codes" in validated_data:
            self._update_event_codes(
                instance,
                validated_data.pop('event_codes'),
            )

        instance = super().update(instance, validated_data)

        if is_include_triangulation_in_qa_changed:
            recipients = [user['id'] for user in Event.regional_coordinators(
                instance,
                actor=self.context['request'].user,
            )]
            if (instance.created_by_id):
                recipients.append(instance.created_by_id)
            if (instance.assignee_id):
                recipients.append(instance.assignee_id)

            Notification.send_safe_multiple_notifications(
                recipients=recipients,
                type=Notification.Type.EVENT_INCLUDE_TRIANGULATION_CHANGED,
                actor=self.context['request'].user,
                event=instance,
            )

            Figure.update_event_status_and_send_notifications(instance.id)
            instance.refresh_from_db()
        return instance


class EventUpdateSerializer(UpdateSerializerMixin, EventSerializer):
    id = IntegerIDField(required=True)
    event_codes = EventCodeUpdateSerializer(many=True, required=True)


class CloneEventSerializer(serializers.Serializer):
    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())

    def save(self, *args, **kwargs):
        event: Event = self.validated_data['event']

        return event.clone_and_save_event(
            user=self.context['request'].user,
        )


class ContextOfViolenceSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ContextOfViolence
        fields = '__all__'


class ContextOfViolenceUpdateSerializer(UpdateSerializerMixin, ContextOfViolenceSerializer):
    """Just to create input type"""
    id = IntegerIDField(required=True)
