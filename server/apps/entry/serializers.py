from django.db import transaction
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
