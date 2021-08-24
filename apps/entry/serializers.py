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
    DisaggregatedAgeCategory,
)
from apps.entry.constants import STOCK
from apps.entry.constants import (
    DISAGGREGATED_AGE_SEX_CHOICES,
)
from apps.event.models import Event
from apps.users.models import User
from apps.users.enums import USER_ROLE
from utils.validations import is_child_parent_inclusion_valid, is_child_parent_dates_valid


class DisaggregatedAgeSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(required=True)
    category = serializers.PrimaryKeyRelatedField(
        queryset=DisaggregatedAgeCategory.objects.all(),
        required=False
    )
    sex = serializers.ChoiceField(
        choices=DISAGGREGATED_AGE_SEX_CHOICES.choices(),
        required=False
    )
    value = serializers.IntegerField(validators=[MinValueValidator(0, _("Minimum value is 1. "))],
                                     required=True)

    def validate(self, attrs):
        # because they are stored inside json
        attrs['uuid'] = str(attrs['uuid'])
        attrs['category'] = getattr(attrs.get('category'), 'id', None)
        return attrs


class DisaggregatedStratumSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(required=True)
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
    id = IntegerIDField(required=False)

    class Meta:
        model = OSMName
        fields = '__all__'
        extra_kwargs = {
            'uuid': {
                'validators': [],
                'required': True
            },
        }


class CommonFigureValidationMixin:
    def get_event(self):
        if not self.parent:
            # this will be the case when we will be using this serializer directly,
            # which will not be the case when in use in the application.
            # this if block currently only is for directly testing this serializer which does not use event
            return None

        if not hasattr(self, 'event'):
            self.event_id = self.parent.parent.initial_data.get('event', None)
            if self.event_id:
                self.event = Event.objects.filter(id=self.event_id).first()
            else:
                self.event = self.parent.parent.instance.event
        return self.event

    def validate_disaggregation_age_json(self, age_groups):
        age_groups = age_groups or []
        values = []
        for each in age_groups:
            values.append((each.get('category'), each.get('sex')))
        if len(values) != len(set(values)):
            raise serializers.ValidationError('Please provide unique age category and sex.')
        return age_groups

    def validate_disaggregation_strata_json(self, strata):
        values = [each['date'] for each in strata]
        if len(values) != len(set(values)):
            raise serializers.ValidationError(
                gettext('Make sure the dates are unique in a figure.'))
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
            errors.update({
                'geo_locations': 'This field is required.'
            })
            return errors
        location_code = country.iso2
        if not location_code:
            # ignore iso2 validation if missing
            return errors
        geo_locations_code = set([
            location['country_code'] for location in attrs['geo_locations']
        ])

        if len(geo_locations_code) != 1:
            errors.update({
                'geo_locations': 'Geolocations only support a single country under a figure.'
            })

        if geo_locations_code.pop().lower() != location_code.lower():
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
        if self.get_event():
            category = attrs.get('category', getattr(self.instance, 'category', None))
            if category.type == STOCK:
                errors.update(is_child_parent_dates_valid(
                    attrs.get('start_date', getattr(self.instance, 'start_date', None)),
                    attrs.get('end_date', getattr(self.instance, 'end_date', None)),
                    self.event.start_date,
                    'event',
                ))
            else:
                errors.update(is_child_parent_dates_valid(
                    attrs.get('start_date', getattr(self.instance, 'start_date', None)),
                    attrs.get('end_date', getattr(self.instance, 'end_date', None)),
                    self.event.start_date,
                    'event',
                ))
        return errors

    def clean_term_with_displacement_occur(self, attrs):
        _attrs = copy(attrs)
        term = attrs.get('term')
        if not term or (term and not term.displacement_occur):
            _attrs['displacement_occurred'] = None
        return _attrs

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
            attrs, ['disaggregation_location_camp', 'disaggregation_location_non_camp'], 'camp and non-camp'
        ))
        errors.update(self.validate_disaggregated_sum_against_reported(
            attrs, ['disaggregation_displacement_urban', 'disaggregation_displacement_rural'], 'urban and rural'
        ))
        errors.update(self.validate_disaggregated_sum_against_reported(
            attrs, ['disaggregation_sex_male', 'disaggregation_sex_female', 'disaggregation_lgbtiq'],
            'male, female and other'
        ))
        errors.update(self.validate_disaggregated_sum_against_reported(
            attrs, ['disaggregation_disability', 'disaggregation_indigenous_people'], 'Disability and indigenous people',
        ))
        errors.update(self.validate_disaggregated_sum_against_reported(
            attrs,
            [
                'disaggregation_conflict',
                'disaggregation_conflict_political',
                'disaggregation_conflict_criminal',
                'disaggregation_conflict_other',
                'disaggregation_conflict_communal'
            ],
            'conflict'
        ))
        errors.update(self.validate_disaggregated_json_sum_against_reported(attrs, 'disaggregation_age_json', 'age'))
        errors.update(self.validate_disaggregated_json_sum_against_reported(attrs, 'disaggregation_strata_json', 'strata'))
        if errors:
            raise ValidationError(errors)

        # update attrs
        attrs = self.clean_term_with_displacement_occur(attrs)
        return attrs


class NestedFigureCreateSerializer(MetaInformationSerializerMixin,
                                   CommonFigureValidationMixin,
                                   serializers.ModelSerializer):
    disaggregation_age_json = DisaggregatedAgeSerializer(many=True, required=False, allow_null=True)
    disaggregation_strata_json = DisaggregatedStratumSerializer(many=True, required=False)
    geo_locations = OSMNameSerializer(many=True, required=False, allow_null=False)

    class Meta:
        model = Figure
        exclude = ('id', 'entry', 'total_figures')
        extra_kwargs = {
            'uuid': {
                'validators': [],
                'required': True
            },
        }

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
            getattr(instance, attr).exclude(
                id__in=[each['id'] for each in data if 'id' in each]
            ).delete()
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
        extra_kwargs = {
            'uuid': {
                'validators': [],
                'required': True
            },
        }

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
                USER_ROLE.ADMIN.name,
                USER_ROLE.MONITORING_EXPERT.name,
                USER_ROLE.REGIONAL_COORDINATOR.name,
            ]
        ),
        required=False
    )

    class Meta:
        model = Entry
        fields = '__all__'

    def validate_figures(self, figures):
        if len(figures) > Entry.FIGURES_PER_ENTRY:
            raise serializers.ValidationError(
                gettext('Too many figures. Limit is %s. Please contact the administrator.' % Entry.FIGURES_PER_ENTRY)
            )
        uuids = [figure['uuid'] for figure in figures]
        if len(uuids) != len(set(uuids)):
            raise serializers.ValidationError(gettext('Duplicate keys found. '))
        geo_uuids = [loc['uuid'] for figure in figures for loc in figure.get('geo_locations', [])]
        if len(geo_uuids) != len(set(geo_uuids)):
            raise serializers.ValidationError(gettext('Duplicate geolocation keys found. '))
        if self.instance:
            if {each['id'] for each in figures if 'id' in each}.difference(
                    list(self.instance.figures.values_list('id', flat=True))
            ):
                raise serializers.ValidationError(gettext('Some figures you are trying to update does'
                                                  'not exist.'))
        return figures

    def validate_calculation_logic(self, value):
        if not value:
            raise serializers.ValidationError(_('This field is required'))
        return value

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


class CloneEntrySerializer(serializers.Serializer):
    events = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all(), many=True)
    entry = serializers.PrimaryKeyRelatedField(queryset=Entry.objects.all())

    def save(self, *args, **kwargs):
        entry: Entry = self.validated_data['entry']

        return entry.clone_and_save_entries(
            event_list=self.validated_data['events'],
            user=self.context['request'].user,
        )
