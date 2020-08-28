from django.db import transaction
from django.utils.translation import gettext
from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.entry.models import Entry, Figure


class CommonFigureValidationMixin:
    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        instance = Figure(**attrs)
        instance.clean()
        return attrs


class FigureSerializer(CommonFigureValidationMixin,
                       MetaInformationSerializerMixin,
                       serializers.ModelSerializer):
    class Meta:
        model = Figure
        fields = '__all__'


class NestedFigureSerializer(CommonFigureValidationMixin,
                             MetaInformationSerializerMixin,
                             serializers.ModelSerializer):
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

    @property
    def errors(self):
        errors = super().errors
        # populate the nested keys here
        if 'figures' in errors and isinstance(errors['figures'][0], dict):
            for pos, item in enumerate(errors['figures']):
                if errors['figures'][pos]:
                    # keys populated here will be popped out while building error
                    errors['figures'][pos]['key'] = self.initial_data['figures'][pos].get('uuid', f'NOT_FOUND_{pos}')
        return errors

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
