from django.core.validators import MinValueValidator
from collections import OrderedDict

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext, gettext_lazy as _
from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.entry.models import Entry, Figure


class DisaggregatedAgeSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(required=False)
    age_from = serializers.IntegerField(validators=[MinValueValidator(0, _("Minimum value is 1. "))],
                                        required=True)
    age_to = serializers.IntegerField(validators=[MinValueValidator(0, _("Minimum value is 1. "))],
                                      required=True)
    value = serializers.IntegerField(validators=[MinValueValidator(0, _("Minimum value is 1. "))],
                                     required=True)

    def validate(self, attrs):
        if attrs.get('age_from') > attrs.get('age_to'):
            raise serializers.ValidationError({'age_to': gettext(f'Pick an age higher than `from` {attrs.get("age_from")}. ')})
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


class CommonFigureValidationMixin:
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
            raise serializers.ValidationError(gettext('Make sure the dates are unique in a figure. '))
        return strata

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        errors = OrderedDict()
        errors.update(Figure.clean_idu(attrs, self.instance))
        if errors:
            raise ValidationError(errors)
        return attrs


class FigureSerializer(MetaInformationSerializerMixin,
                       CommonFigureValidationMixin,
                       serializers.ModelSerializer):
    age_json = DisaggregatedAgeSerializer(many=True, required=False)
    strata_json = DisaggregatedStratumSerializer(many=True, required=False)

    class Meta:
        model = Figure
        fields = '__all__'

    def create(self, validated_data: dict) -> Figure:
        # serializer with nested serializer(many=True), requires custom `create`
        # despite in our case they are JSONFields
        return Figure.objects.create(**validated_data)


class NestedFigureSerializer(MetaInformationSerializerMixin,
                             CommonFigureValidationMixin,
                             serializers.ModelSerializer):
    age_json = DisaggregatedAgeSerializer(many=True, required=False)
    strata_json = DisaggregatedStratumSerializer(many=True, required=False)

    class Meta:
        model = Figure
        exclude = ('entry',)


class EntrySerializer(MetaInformationSerializerMixin,
                      serializers.ModelSerializer):
    figures = NestedFigureSerializer(many=True, required=False)

    class Meta:
        model = Entry
        fields = '__all__'

    def validate_figures(self, figures):
        uuids = [figure['uuid'] for figure in figures]
        if len(uuids) != len(set(uuids)):
            raise serializers.ValidationError('Duplicate keys found. ')
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
                Figure.objects.bulk_create([
                    Figure(**each, entry=entry) for each in figures
                ])
        else:
            entry = super().create(validated_data)
        return entry
