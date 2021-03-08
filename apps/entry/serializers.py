from collections import OrderedDict
from copy import copy

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import transaction
from django.utils.translation import gettext, gettext_lazy as _
from rest_framework import serializers

from apps.contrib.serializers import (
    MetaInformationSerializerMixin,
    UpdateSerializerMixin,
    IntegerIDField,
)
from apps.entry.models import (
    Entry,
    Figure,
    OSMName,
    EntryReviewer,
    FigureTag,
)
from apps.event.models import Event
from apps.users.models import User
from apps.users.enums import USER_ROLE
from utils.validations import is_child_parent_inclusion_valid


class DisaggregatedAgeSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(required=False)
    age_from = serializers.IntegerField(
        validators=[MinValueValidator(0, _("Minimum value is 1. "))],
        required=True)
    age_to = serializers.IntegerField(validators=[MinValueValidator(0, _("Minimum value is 1. "))],
                                      required=True)
    value = serializers.IntegerField(validators=[MinValueValidator(0, _("Minimum value is 1. "))],
                                     required=True)

    def validate(self, attrs):
        if attrs.get('age_from') > attrs.get('age_to'):
            raise serializers.ValidationError(
                {'age_to': gettext('Pick an age higher than `from` %(age_from)s.') %
                    {'age_from': attrs.get("age_from")}}
            )
        attrs['uuid'] = str(attrs['uuid'])
        return attrs


class DisaggregatedStratumSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(required=False)
    date = serializers.DateField(required=True)
    value = serializers.IntegerField(validators=[MinValueValidator(0, _("Minimum value is 1. "))],
                                     required=True)

    def validate(self, attrs: dict) -> dict:
        # in order to store into the JSONField
        attrs['uuid'] = str(attrs['uuid'])
        attrs['date'] = str(attrs['date'])
        return attrs


class OSMNameSerializer(serializers.ModelSerializer):
    # to allow updating
    uuid = serializers.UUIDField(required=False)
    id = IntegerIDField(required=False)

    class Meta:
        model = OSMName
        fields = '__all__'


class CommonFigureValidationMixin:
    def get_event(self):
        if not self.parent:
            # this will be the case when we will be using this serializer directly,
            # which will not be the case when in use in the application.
            # this if block currently only is for directly testing this serializer which does not use event
            return None

        if not hasattr(self, 'event_id'):
            self.event_id = self.parent.parent.initial_data.get('event', None)
            if self.event_id:
                self.event = Event.objects.filter(id=self.event_id).first()
            else:
                self.event = self.parent.parent.instance.event
                self.event_id = self.event.id
        return self.event

    def validate_age_json(self, age_groups):
        values = []
        for each in age_groups:
            values.extend(range(each['age_from'], each['age_to']))
        if len(values) != len(set(values)):
            raise serializers.ValidationError(gettext('Please do not mix up age ranges. '))
        return age_groups

    def validate_strata_json(self, strata):
        values = [each['date'] for each in strata]
        if len(values) != len(set(values)):
            raise serializers.ValidationError(
                gettext('Make sure the dates are unique in a figure. '))
        return strata

    def validate_unit_and_household_size(self, attrs):
        errors = OrderedDict()
        if attrs.get('unit',
                     getattr(self.instance, 'unit', Figure.UNIT.PERSON.value) ==
                     Figure.UNIT.HOUSEHOLD.value) and \
                not attrs.get('household_size',
                              getattr(self.instance, 'household_size', 0)):
            raise serializers.ValidationError(
                dict(household_size=gettext('Please pass in household size for household unit.'))
            )
        return errors

    def validate_figure_geo_locations(self, attrs):
        errors = OrderedDict()
        country = attrs.get('country')
        if not country and self.instance:
            country = self.instance.country
        if not attrs.get('geo_locations'):
            return errors
        location_code = country.country_code
        geo_locations_code = set([
            location['country_code'] for location in attrs['geo_locations']
        ])

        if len(geo_locations_code) != 1:
            errors.update({
                'geo_locations': 'Geolocations only support a single country under a figure.'
            })

        if int(geo_locations_code.pop()) != int(location_code):
            errors.update({
                'geo_locations': "Location should be inside the selected figure's country"
            })
        return errors

    def validate_disaggregated_sum_against_reported(self, attrs, fields, verbose_names):
        errors = OrderedDict()
        reported = attrs.get('reported', getattr(self.instance, 'reported', 0)) or 0
        disaggregated_sum = 0
        for field in fields:
            disaggregated_sum += attrs.get(field, getattr(self.instance, field, 0)) or 0
        if disaggregated_sum > reported:
            errors.update({
                field: f'Sum of {verbose_names} figures is greater than reported.'
                for field in fields
            })
        return errors

    def validate_disaggregated_json_sum_against_reported(self, attrs, field, verbose_name):
        errors = OrderedDict()
        reported = attrs.get('reported') or getattr(self.instance, 'reported', None) or 0
        json_field = attrs.get(field) or getattr(self.instance, field, None) or []
        total = [item['value'] for item in json_field]
        if sum(total) > reported:
            errors.update({
                field: f'Sum of {verbose_name} figures is greater than reported.'
            })
        return errors

    def _validate_geo_locations(self, geo_locations) -> list:
        if self.instance:
            if {each['id'] for each in geo_locations if 'id' in each}.difference(
                    list(self.instance.geo_locations.values_list('id', flat=True))
            ):
                raise serializers.ValidationError(
                    dict(geo_locations='Some geo locations not found.')
                )
        return geo_locations

    def validate_figure_country(self, attrs):
        _attrs = copy(attrs)
        errors = OrderedDict()
        if self.get_event():
            _attrs.update({'entry': {'event': self.event}})
            errors.update(is_child_parent_inclusion_valid(
                _attrs,
                self.instance,
                'country',
                'entry.event.countries',
            ))
        return errors

    def validate_dates(self, attrs):
        errors = OrderedDict()
        _attrs = copy(attrs)
        if self.get_event():
            _attrs.update({'entry': {'event': self.event}})
            errors.update(Figure.validate_dates(attrs, self.instance))
        return errors

    def validate(self, attrs: dict) -> dict:
        if not self.instance and attrs.get('id'):
            self.instance = Figure.objects.get(id=attrs['id'])
        self._validate_geo_locations(attrs.get('geo_locations', []))
        attrs = super().validate(attrs)
        errors = OrderedDict()
        errors.update(Figure.clean_idu(attrs, self.instance))
        errors.update(self.validate_unit_and_household_size(attrs))
        errors.update(self.validate_dates(attrs))
        errors.update(self.validate_figure_country(attrs))
        errors.update(self.validate_figure_geo_locations(attrs))
        errors.update(self.validate_disaggregated_sum_against_reported(
            attrs, ['location_camp', 'location_non_camp'], 'camp and non-camp'
        ))
        errors.update(self.validate_disaggregated_sum_against_reported(
            attrs, ['displacement_urban', 'displacement_rural'], 'urban and rural'
        ))
        errors.update(self.validate_disaggregated_sum_against_reported(
            attrs, ['sex_male', 'sex_female'], 'male and female'
        ))
        errors.update(self.validate_disaggregated_sum_against_reported(
            attrs,
            ['conflict', 'conflict_political', 'conflict_criminal', 'conflict_other', 'conflict_communal'],
            'conflict'
        ))
        errors.update(self.validate_disaggregated_json_sum_against_reported(attrs, 'age_json', 'age'))
        errors.update(self.validate_disaggregated_json_sum_against_reported(attrs, 'strata_json', 'strata'))
        if errors:
            raise ValidationError(errors)
        return attrs


class NestedFigureCreateSerializer(MetaInformationSerializerMixin,
                                   CommonFigureValidationMixin,
                                   serializers.ModelSerializer):
    age_json = DisaggregatedAgeSerializer(many=True, required=False)
    strata_json = DisaggregatedStratumSerializer(many=True, required=False)
    geo_locations = OSMNameSerializer(many=True, required=False)
    uuid = serializers.CharField(required=True)

    class Meta:
        model = Figure
        exclude = ('id', 'entry', 'total_figures')

    def create(self, validated_data: dict) -> Figure:
        geo_locations = validated_data.pop('geo_locations', [])
        if geo_locations:
            geo_locations = OSMName.objects.bulk_create(
                [OSMName(**each) for each in geo_locations]
            )
        instance = Figure.objects.create(**validated_data)
        instance.geo_locations.set(geo_locations)
        return instance

    def _update_locations(self, instance, attr: str, data: list):
        osms = []
        if data:
            getattr(instance, attr).exclude(id__in=[each['id'] for each in data if 'id'
                                                    in each]).delete()
            for each in data:
                if not each.get('id'):
                    osm_serializer = OSMNameSerializer()
                    osm_serializer._validated_data = {**each}
                else:
                    osm_serializer = OSMNameSerializer(
                        instance=getattr(instance, attr).get(id=each['id']),
                        # instance=OSMName.objects.get(id=each['id']),
                        partial=True
                    )
                    osm_serializer._validated_data = {**each}
                osm_serializer._errors = {}
                osms.append(osm_serializer.save())
        getattr(instance, attr).set(osms)

    def update(self, instance, validated_data):
        geo_locations = validated_data.pop('geo_locations', [])
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            self._update_locations(instance=instance,
                                   attr='geo_locations',
                                   data=geo_locations)
        return instance


class NestedFigureUpdateSerializer(NestedFigureCreateSerializer):
    id = IntegerIDField(required=False)

    class Meta:
        model = Figure
        exclude = ('entry', 'total_figures')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # all updates will be a patch update
        for name in self.fields:
            self.fields[name].required = False


class EntryCreateSerializer(MetaInformationSerializerMixin,
                            serializers.ModelSerializer):
    figures = NestedFigureCreateSerializer(many=True, required=False)
    reviewers = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.filter(
            groups__name__in=[
                USER_ROLE.IT_HEAD.name,
                USER_ROLE.ADMIN.name,
                USER_ROLE.MONITORING_EXPERT_REVIEWER.name,
                USER_ROLE.MONITORING_EXPERT_EDITOR.name,
            ]
        ),
        required=False
    )

    class Meta:
        model = Entry
        fields = '__all__'

    def validate_figures(self, figures):
        uuids = [figure['uuid'] for figure in figures]
        if len(uuids) != len(set(uuids)):
            raise serializers.ValidationError('Duplicate keys found. ')
        if self.instance:
            if {each['id'] for each in figures if 'id' in each}.difference(
                    list(self.instance.figures.values_list('id', flat=True))
            ):
                raise serializers.ValidationError('Some figures you are trying to update does'
                                                  'not exist.')
        return figures

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        errors = OrderedDict()
        errors.update(Entry.clean_url_and_document(attrs, self.instance))
        if errors:
            raise ValidationError(errors)
        return attrs

    def create(self, validated_data: dict) -> Entry:
        figures = validated_data.pop('figures', [])
        if figures:
            with transaction.atomic():
                entry = super().create(validated_data)
                for each in figures:
                    # each figure contains further nested objects
                    fig_ser = NestedFigureCreateSerializer()
                    fig_ser._validated_data = {**each, 'entry': entry}
                    fig_ser._errors = {}
                    fig_ser.save()
        else:
            entry = super().create(validated_data)
        EntryReviewer.assign_creator(entry=entry,
                                     user=self.context['request'].user)
        return entry

    def update(self, instance, validated_data: dict) -> Entry:
        figures = validated_data.pop('figures', [])
        if figures:
            with transaction.atomic():
                entry = super().update(instance, validated_data)
                # delete missing figures
                entry.figures.exclude(
                    id__in=[each['id'] for each in figures if each.get('id')]).delete()
                # create if has no ids
                for each in figures:
                    if not each.get('id'):
                        fig_ser = NestedFigureCreateSerializer()
                        fig_ser._validated_data = {**each, 'entry': entry}
                    else:
                        fig_ser = NestedFigureUpdateSerializer(
                            instance=entry.figures.get(id=each['id']),
                            partial=True
                        )
                        fig_ser._validated_data = {**each, 'entry': entry}
                    fig_ser._errors = {}
                    fig_ser.save()
        else:
            entry = super().update(instance, validated_data)
        return entry


class EntryUpdateSerializer(UpdateSerializerMixin,
                            EntryCreateSerializer):
    """Created for update mutation input type"""
    id = IntegerIDField(required=True)
    figures = NestedFigureUpdateSerializer(many=True, required=True)


class FigureTagCreateSerializer(MetaInformationSerializerMixin,
                                serializers.ModelSerializer):
    class Meta:
        model = FigureTag
        fields = '__all__'


class FigureTagUpdateSerializer(UpdateSerializerMixin,
                                FigureTagCreateSerializer):
    id = IntegerIDField(required=True)
