from django.core.validators import MinValueValidator
from collections import OrderedDict

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext, gettext_lazy as _
from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.entry.models import Entry, Figure, SourcePreview

CANNOT_UPDATE_FIGURE = 'You cannot update this figure.'


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


class NestedFigureUpdateSerializer(MetaInformationSerializerMixin,
                                   CommonFigureValidationMixin,
                                   serializers.ModelSerializer):
    age_json = DisaggregatedAgeSerializer(many=True, required=False)
    strata_json = DisaggregatedStratumSerializer(many=True, required=False)
    id = serializers.IntegerField(required=True)  # overwrite the default id field

    class Meta:
        model = Figure
        fields = '__all__'

    def validate(self, attrs: dict) -> dict:
        try:
            figure = Figure.objects.get(id=attrs['id'])
        except Figure.DoesNotExist:
            raise serializers.ValidationError('Figure does not exist.')
        if not figure.can_be_updated_by(self.context['request'].user):
            raise serializers.ValidationError(gettext(CANNOT_UPDATE_FIGURE))
        return attrs


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


class EntryFiguresOnlyCreateSerializer(serializers.Serializer):
    entry = serializers.IntegerField(required=True)
    figures = NestedFigureSerializer(many=True, required=False)

    def validate_entry(self, entry_id: int):
        if not Entry.objects.filter(id=entry_id).exists():
            raise serializers.ValidationError(gettext('Entry does not exist.'))
        return entry_id

    def validate_figures(self, figures: list):
        uuids = [figure['uuid'] for figure in figures]
        if len(uuids) != len(set(uuids)):
            raise serializers.ValidationError('Duplicate keys found. ')
        return figures

    def create(self, validated_data: dict):
        figures = validated_data.pop('figures', [])
        entry_id = validated_data.pop('entry', None)
        objects = []
        if figures:
            objects = Figure.objects.bulk_create([
                Figure(**each, entry_id=entry_id) for each in figures
            ])
        return objects


class EntryFiguresOnlyUpdateSerializer(serializers.Serializer):
    entry = serializers.IntegerField(required=False)
    figures = NestedFigureUpdateSerializer(many=True, required=False)

    def validate_figures(self, figures: list):
        uuids = [figure.get('uuid', None) for figure in figures]
        if all(uuids) and len(uuids) != len(set(uuids)):
            raise serializers.ValidationError('Duplicate keys found. ')
        return figures

    def save(self, **kwargs):
        validated_data = {**self.validated_data, **kwargs}
        figures = validated_data.pop('figures', [])
        objects = []
        for each in figures:
            figure = Figure.objects.get(id=each['id'])
            for k, v in each.items():
                setattr(figure, k, v)
            figure.save()
            objects.append(figure)
        return objects


class SourcePreviewSerializer(MetaInformationSerializerMixin,
                              serializers.ModelSerializer):
    class Meta:
        model = SourcePreview
        fields = '__all__'

    def create(self, validated_data):
        return SourcePreview.get_pdf(**validated_data)

    def update(self, instance, validated_data):
        return SourcePreview.get_pdf(**validated_data, instance=instance)
