from collections import OrderedDict
from copy import copy

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import transaction
from django.utils.translation import gettext, gettext_lazy as _
from rest_framework import serializers
from rest_framework.fields import CharField

from apps.contrib.serializers import (
    MetaInformationSerializerMixin,
    UpdateSerializerMixin,
    IntegerIDField,
)
from apps.entry.models import (
    Entry,
    Figure,
    OSMName,
    FigureTag,
    DisaggregatedAge,
)
from apps.country.models import Country
from apps.notification.models import Notification
from utils.validations import is_child_parent_inclusion_valid, is_child_parent_dates_valid
from utils.common import round_half_up


class DisaggregatedAgeSerializer(serializers.ModelSerializer):
    # to allow updating
    id = IntegerIDField(required=False)

    def validate(self, attrs):
        errors = OrderedDict()
        age_from = attrs.get('age_from')
        age_to = attrs.get('age_to')

        if (age_from and not age_to):
            errors['age_to'] = gettext('This field is required.')
        if (age_to and not age_from):
            errors['age_from'] = gettext('This field is required.')
        return attrs

    class Meta:
        model = DisaggregatedAge
        fields = '__all__'
        extra_kwargs = {
            'uuid': {
                'validators': [],
                'required': True
            },
        }


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
    country = CharField(required=False, allow_blank=True)

    def validate(self, attrs: dict) -> dict:
        '''
        NOTE: In some cases osmname api does not provides country,
        in this case get country from country code
        '''
        if not self.instance and not attrs.get('country'):
            country_code = attrs.get('country_code', '').upper()
            country = Country.objects.filter(iso2__iexact=country_code).first()
            if not country:
                raise serializers.ValidationError('Country field is required.')
            attrs['country'] = country
        return attrs

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

    def validate_disaggregation_age(self, age_groups):
        age_groups = age_groups or []
        values = []
        for each in age_groups:
            values.append((each.get('age_from'), each.get('age_to'), each.get('sex')))
        if len(values) != len(set(values)):
            raise serializers.ValidationError('Please provide unique age range and sex.')
        return age_groups

    def validate_disaggregation_strata_json(self, strata):
        values = [each['date'] for each in strata]
        if len(values) != len(set(values)):
            raise serializers.ValidationError(
                gettext('Make sure the dates are unique in a figure.'))
        return strata

    def _validate_unit_and_household_size(self, attrs):
        errors = OrderedDict()

        unit = attrs.get('unit', getattr(self.instance, 'unit', Figure.UNIT.PERSON))
        household_size = attrs.get('household_size', getattr(self.instance, 'household_size', 0))

        if unit == Figure.UNIT.HOUSEHOLD and not household_size:
            errors.update({
                'household_size': 'Please pass in household size for household unit.'
            })
        return errors

    def _validate_figure_geo_locations(self, attrs):
        errors = OrderedDict()
        country = attrs.get('country')
        geo_locations = attrs.get('geo_locations', None)
        if not country and self.instance:
            country = self.instance.country
        if not geo_locations:
            errors.update({
                'geo_locations': 'This field is required.'
            })
            return errors
        country_code = country.iso2
        if not country_code:
            # ignore iso2 validation if missing
            return errors
        for location in geo_locations:
            # If location is moved manually allow to save location of other coutries
            # These locations are considered as problematic border issues
            moved = location.get("moved", False)
            if country_code not in Figure.SUPPORTED_OSMNAME_COUNTRY_CODES:
                continue
            elif location.get("country_code", '').lower() != country_code.lower() and not moved:
                errors.update({
                    'geo_locations': "Location should be inside the selected figure's country"
                })
        return errors

    def _validate_disaggregated_sum_against_total_figures(self, attrs, fields, verbose_names):
        def _format_message(fields, verbose_names):
            if len(fields) > 1:
                return f'Sum of {verbose_names} figures is greater than total figures.'
            return f'{verbose_names} figures is greater than total figures.'

        errors = OrderedDict()

        total_figures = attrs.get('total_figures')

        disaggregated_sum = 0
        for field in fields:
            disaggregated_sum += attrs.get(field, getattr(self.instance, field, 0)) or 0

        if disaggregated_sum > total_figures:
            errors.update({
                field: _format_message(fields, verbose_names)
                for field in fields
            })
        return errors

    def _validate_disaggregated_json_sum_against_total_figures(self, attrs, field, verbose_name):
        errors = OrderedDict()

        total_figures = attrs.get('total_figures')

        json_field = attrs.get(field) or getattr(self.instance, field, None) or []
        if not isinstance(json_field, list):
            return errors
        total = sum([item['value'] for item in json_field])

        if total > total_figures:
            errors.update({
                field: f'Sum of {verbose_name} figures is greater than total figures.'
            })
        return errors

    def _validate_geo_locations(self, attrs):
        _attrs = copy(attrs)
        errors = OrderedDict()

        geo_locations = _attrs.get('geo_locations', None)

        # FIXME: why only check when creating entry
        if self.instance and geo_locations:
            geo_location_ids = {geo_location['id'] for geo_location in geo_locations if 'id' in geo_location}
            geo_locations_on_db = list(
                self.instance.geo_locations.values_list('id', flat=True)
            ) if self.instance.geo_locations else []
            if geo_location_ids.difference(geo_locations_on_db):
                errors['geo_locations'] = 'Some geo locations not found.'

        return errors

    def _validate_figure_country(self, attrs):
        _attrs = copy(attrs)
        errors = OrderedDict()

        event = attrs.get('event', getattr(self.instance, 'event', None))

        if event:
            errors.update(is_child_parent_inclusion_valid(
                _attrs,
                self.instance,
                'country',
                'event.countries',
            ))
        return errors

    def _validate_dates(self, attrs):
        errors = OrderedDict()
        event = attrs.get('event', getattr(self.instance, 'event', None))

        if event:
            errors.update(is_child_parent_dates_valid(
                attrs.get('start_date', getattr(self.instance, 'start_date', None)),
                attrs.get('end_date', getattr(self.instance, 'end_date', None)),
                event.start_date,
                'event',
            ))
        return errors

    def _validate_idu(self, attrs):
        errors = OrderedDict()
        if attrs.get('include_idu', getattr(self.instance, 'include_idu', None)):
            excerpt_idu = attrs.get('excerpt_idu', getattr(self.instance, 'excerpt_idu', None))
            if excerpt_idu is None or not excerpt_idu.strip():
                errors['excerpt_idu'] = gettext('This field is required.')
        return errors

    def _validate_figure_cause(self, attrs):
        errors = OrderedDict()

        event = attrs.get('event', getattr(self.instance, 'event', None))
        figure_cause = attrs.get('figure_cause', getattr(self.instance, 'figure_cause', None))

        if figure_cause and event and event.event_type.value != figure_cause:
            errors.update({
                'figure_cause': f'Figure cause should be {event.event_type.label}'
            })
        return errors

    def clean_total_figures(self, attrs):
        _attrs = copy(attrs)
        if self.instance:
            unit = _attrs.get('unit', self.instance.unit) or Figure.UNIT.PERSON
            reported = _attrs.get('reported', self.instance.reported) or 0
            household_size = _attrs.get('household_size', self.instance.household_size) or 0
        else:
            unit = _attrs.get('unit') or Figure.UNIT.PERSON
            reported = _attrs.get('reported') or 0
            household_size = _attrs.get('household_size') or 0

        total_figures = 0
        if unit == Figure.UNIT.HOUSEHOLD:
            total_figures = round_half_up(reported * household_size)
        else:
            total_figures = reported
        _attrs['total_figures'] = total_figures

        return _attrs

    def clean_term_with_displacement_occur(self, attrs):
        _attrs = copy(attrs)

        term = _attrs.get('term', getattr(self.instance, 'term', None))
        if term is None or term not in Figure.displacement_occur_list():
            _attrs['displacement_occurred'] = None
        return _attrs

    def validate(self, attrs: dict) -> dict:
        if not self.instance and attrs.get('id'):
            self.instance = Figure.objects.get(id=attrs['id'])

        attrs = super().validate(attrs)

        errors = OrderedDict()

        # NOTE: calculate attributes
        attrs = self.clean_total_figures(attrs)
        attrs = self.clean_term_with_displacement_occur(attrs)

        errors.update(self._validate_idu(attrs))
        errors.update(self._validate_unit_and_household_size(attrs))
        errors.update(self._validate_geo_locations(attrs))
        errors.update(self._validate_dates(attrs))
        errors.update(self._validate_figure_country(attrs))
        errors.update(self._validate_figure_geo_locations(attrs))
        errors.update(self._validate_disaggregated_sum_against_total_figures(
            attrs, ['disaggregation_location_camp', 'disaggregation_location_non_camp'], 'camp and non-camp'
        ))
        errors.update(self._validate_disaggregated_sum_against_total_figures(
            attrs, ['disaggregation_displacement_urban', 'disaggregation_displacement_rural'], 'urban and rural'
        ))
        errors.update(self._validate_disaggregated_sum_against_total_figures(
            attrs, ['disaggregation_disability'], 'Disability',
        ))
        errors.update(self._validate_disaggregated_sum_against_total_figures(
            attrs, ['disaggregation_indigenous_people'], 'Indigenous people',
        ))
        errors.update(self._validate_disaggregated_json_sum_against_total_figures(attrs, 'disaggregation_age', 'age'))
        errors.update(self._validate_figure_cause(attrs))

        if errors:
            raise ValidationError(errors)

        return attrs


class FigureTagSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = FigureTag
        fields = '__all__'


class NestedFigureCreateSerializer(MetaInformationSerializerMixin,
                                   CommonFigureValidationMixin,
                                   serializers.ModelSerializer):
    disaggregation_age = DisaggregatedAgeSerializer(many=True, required=False, allow_null=False)
    disaggregation_strata_json = DisaggregatedStratumSerializer(many=True, required=False)
    geo_locations = OSMNameSerializer(many=True, required=False, allow_null=False)

    class Meta:
        model = Figure
        fields = [
            'was_subfact',
            'quantifier',
            'reported',
            'unit',
            'household_size',
            'category',
            'term',
            'displacement_occurred',
            'role',
            'start_date',
            'start_date_accuracy',
            'end_date',
            'end_date_accuracy',
            'include_idu',
            'excerpt_idu',
            'country',
            'is_disaggregated',
            'is_housing_destruction',
            'geo_locations',
            'calculation_logic',
            'tags',
            'source_excerpt',
            'event',
            'context_of_violence',
            'figure_cause',
            'violence',
            'violence_sub_type',
            'disaster_category',
            'disaster_sub_category',
            'disaster_type',
            'disaster_sub_type',
            'other_sub_type',
            'osv_sub_type',
            'sources',
            # UUID abstract fields
            'uuid',
            # Figure disaggregation abstract fields
            'disaggregation_displacement_urban',
            'disaggregation_displacement_rural',
            'disaggregation_location_camp',
            'disaggregation_location_non_camp',
            'disaggregation_lgbtiq',
            'disaggregation_disability',
            'disaggregation_indigenous_people',
            'disaggregation_sex_male',
            'disaggregation_sex_female',
            'disaggregation_age',
            'disaggregation_strata_json',
            'disaggregation_conflict',
            'disaggregation_conflict_political',
            'disaggregation_conflict_criminal',
            'disaggregation_conflict_communal',
            'disaggregation_conflict_other',
            'disaggregation_age',
            'disaggregation_strata_json',
            'geo_locations'
        ]
        extra_kwargs = {
            'uuid': {
                'validators': [],
                'required': True
            },
        }

    def create(self, validated_data: dict) -> Figure:
        validated_data['created_by'] = self.context['request'].user
        geo_locations = validated_data.pop('geo_locations', [])
        tags = validated_data.pop('tags', [])
        context_of_violence = validated_data.pop('context_of_violence', [])
        disaggregation_ages = validated_data.pop('disaggregation_age', [])
        sources = validated_data.pop('sources', [])
        if geo_locations:
            geo_locations = OSMName.objects.bulk_create(
                [OSMName(**each) for each in geo_locations]
            )

        if disaggregation_ages:
            disaggregation_ages = DisaggregatedAge.objects.bulk_create(
                [DisaggregatedAge(**age_dict) for age_dict in disaggregation_ages]
            )

        instance = Figure.objects.create(**validated_data)
        instance.geo_locations.set(geo_locations)
        instance.tags.set(tags)
        instance.context_of_violence.set(context_of_violence)
        instance.disaggregation_age.set(disaggregation_ages)
        instance.sources.set(sources)
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

    def _update_disaggregation_age(self, instance, attr: str, data: list):
        disaggregation_age = []
        if data:
            getattr(instance, attr).exclude(
                id__in=[each['id'] for each in data if 'id' in each]
            ).delete()
            for each in data:
                if not each.get('id'):
                    age_serializer = DisaggregatedAgeSerializer()
                    age_serializer._validated_data = {**each}
                else:
                    age_serializer = DisaggregatedAgeSerializer(
                        instance=getattr(instance, attr).get(id=each['id']),
                        partial=True
                    )
                    age_serializer._validated_data = {**each}
                age_serializer._errors = {}
                disaggregation_age.append(age_serializer.save())
        getattr(instance, attr).set(disaggregation_age)

    def update(self, instance, validated_data):
        validated_data['last_modified_by'] = self.context['request'].user
        geo_locations = validated_data.pop('geo_locations', [])
        tags = validated_data.pop('tags', [])
        context_of_violence = validated_data.pop('context_of_violence', [])
        disaggregation_age = validated_data.pop('disaggregation_age', [])
        sources = validated_data.pop('sources', [])
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            self._update_locations(instance=instance,
                                   attr='geo_locations',
                                   data=geo_locations)
            if disaggregation_age:
                self._update_disaggregation_age(
                    instance=instance,
                    attr="disaggregation_age",
                    data=disaggregation_age
                )
            if tags:
                instance.tags.set(tags)
            if context_of_violence:
                instance.context_of_violence.set(context_of_violence)
            if sources:
                instance.sources.set(sources)
        return instance


class NestedFigureUpdateSerializer(NestedFigureCreateSerializer):
    id = IntegerIDField(required=False)

    class Meta:
        model = Figure
        fields = [
            'id',
            'was_subfact',
            'quantifier',
            'reported',
            'unit',
            'household_size',
            'category',
            'term',
            'displacement_occurred',
            'role',
            'start_date',
            'start_date_accuracy',
            'end_date',
            'end_date_accuracy',
            'include_idu',
            'excerpt_idu',
            'country',
            'is_disaggregated',
            'is_housing_destruction',
            'geo_locations',
            'calculation_logic',
            'tags',
            'source_excerpt',
            'event',
            'context_of_violence',
            'figure_cause',
            'violence',
            'violence_sub_type',
            'disaster_category',
            'disaster_sub_category',
            'disaster_type',
            'disaster_sub_type',
            'other_sub_type',
            'osv_sub_type',
            'sources',
            # UUID abstract fields
            'uuid',
            # Figure disaggregation abstract fields
            'disaggregation_displacement_urban',
            'disaggregation_displacement_rural',
            'disaggregation_location_camp',
            'disaggregation_location_non_camp',
            'disaggregation_lgbtiq',
            'disaggregation_disability',
            'disaggregation_indigenous_people',
            'disaggregation_sex_male',
            'disaggregation_sex_female',
            'disaggregation_age',
            'disaggregation_strata_json',
            'disaggregation_conflict',
            'disaggregation_conflict_political',
            'disaggregation_conflict_criminal',
            'disaggregation_conflict_communal',
            'disaggregation_conflict_other',
            'disaggregation_age',
            'disaggregation_strata_json',
            'geo_locations'
        ]
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

    class Meta:
        model = Entry
        exclude = ('review_status',)

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
                    fig_ser = NestedFigureCreateSerializer(context=self.context)
                    fig_ser._validated_data = {**each, 'entry': entry}
                    fig_ser._errors = {}
                    fig_ser.save()
        else:
            entry = super().create(validated_data)
        return entry

    def update(self, instance, validated_data: dict) -> Entry:
        figures = validated_data.pop('figures', None)
        if figures:
            with transaction.atomic():
                entry = super().update(instance, validated_data)
                # delete missing figures
                entry.figures.exclude(
                    id__in=[each['id'] for each in figures if each.get('id')]).delete()
                # create if has no ids
                created = False
                for each in figures:
                    if not each.get('id'):
                        created = True
                        fig_ser = NestedFigureCreateSerializer(context=self.context)
                        fig_ser._validated_data = {**each, 'entry': entry}
                    else:
                        created = False
                        fig_ser = NestedFigureUpdateSerializer(
                            instance=entry.figures.get(id=each['id']),
                            partial=True,
                            context=self.context,
                        )
                        fig_ser._validated_data = {**each, 'entry': entry}
                    fig_ser._errors = {}
                    figure = fig_ser.save()
                    if figure.event:
                        for coordinator in figure.event.regional_coordinators:
                            Notification.send_notification(
                                recipient=coordinator,
                                actor=self.context['request'].user,
                                figure=figure,
                                event=figure.event,
                                type=Notification.Type.FIGURE_CREATED if created else Notification.Type.FIGURE_UPDATED,
                            )
                        if figure.event.assignee:
                            Notification.send_notification(
                                recipient=figure.event.assignee,
                                actor=self.context['request'].user,
                                figure=figure,
                                event=figure.event,
                                type=Notification.Type.FIGURE_CREATED if created else Notification.Type.FIGURE_UPDATED,
                            )
                    new_event_id = each.get('event_id')
                    old_event_id = fig_ser.data.get('event_id')
                    # Change if event id changed and update event review status
                    if new_event_id != old_event_id:
                        Figure.update_event_status(old_event_id)

        elif isinstance(figures, list) and not figures:
            # If figure is empty list remove all figures associated with entry
            Figure.objects.filter(entry=instance).delete()

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


class FigureReadOnlySerializer(serializers.ModelSerializer):
    country = serializers.CharField(source='country_name')
    iso3 = serializers.CharField()
    latitude = serializers.FloatField(source='centroid_lat')
    longitude = serializers.FloatField(source='centroid_lon')
    centroid = serializers.CharField()
    displacement_type = serializers.CharField(source='figure_cause')
    qualifier = serializers.CharField(source='quantifier_label')
    figure = serializers.IntegerField(source='total_figures')
    displacement_start_date = serializers.CharField()
    displacement_end_date = serializers.CharField()
    displacement_date = serializers.CharField()
    event_name = serializers.CharField()
    event_start_date = serializers.CharField()
    event_end_date = serializers.CharField()
    category = serializers.CharField(source='disaster_category_name')
    subcategory = serializers.CharField(source='disaster_sub_category_name')
    type = serializers.CharField(source='disaster_type_name')
    subtype = serializers.CharField(source='disaster_sub_type_name')
    year = serializers.IntegerField()
    standard_popup_text = serializers.CharField()
    standard_info_text = serializers.CharField()

    class Meta:
        model = Figure
        fields = (
            'id',
            'country',
            'iso3',
            'latitude',
            'longitude',
            'centroid',
            'displacement_type',
            'qualifier',
            'figure',
            'displacement_date',
            'displacement_start_date',
            'displacement_end_date',
            'year',
            'event_name',
            'event_start_date',
            'event_end_date',
            'category',
            'subcategory',
            'type',
            'subtype',
            'standard_popup_text',
            'standard_info_text',
            'old_id',
            'created_at',
        )
