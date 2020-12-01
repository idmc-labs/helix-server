from django.core.validators import MinValueValidator
from collections import OrderedDict

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext, gettext_lazy as _
from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.entry.models import Entry, Figure, SourcePreview, OSMName, EntryReviewer
from apps.users.models import User


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


class OSMNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = OSMName
        fields = '__all__'


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
    source = OSMNameSerializer(required=False)
    destination = OSMNameSerializer(required=False)

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
    source = OSMNameSerializer(required=False)
    destination = OSMNameSerializer(required=False)
    # to allow updating
    id = serializers.IntegerField(required=False)
    uuid = serializers.CharField(required=False)

    class Meta:
        model = Figure
        exclude = ('entry',)

    def create(self, validated_data):
        source_data = validated_data.pop('source', {})
        if source_data:
            source = OSMName.objects.create(**source_data)
            validated_data['source'] = source
        destination_data = validated_data.pop('destination', {})
        if destination_data:
            destination = OSMName.objects.create(**destination_data)
            validated_data['destination'] = destination
        return Figure.objects.create(**validated_data)

    def update(self, instance, validated_data):
        source_data = validated_data.pop('source', {})
        if source_data:
            OSMName.objects.filter(id=instance.source.id).update(**source_data)
        destination_data = validated_data.pop('destination', {})
        if destination_data:
            OSMName.objects.filter(id=instance.destination.id).update(**destination_data)
        return super().update(instance, {**validated_data})


class EntrySerializer(MetaInformationSerializerMixin,
                      serializers.ModelSerializer):
    figures = NestedFigureSerializer(many=True, required=False)
    reviewers = serializers.ListField(child=serializers.IntegerField(), required=False)

    class Meta:
        model = Entry
        fields = '__all__'

    def validate_figures(self, figures):
        uuids = [figure['uuid'] for figure in figures]
        if len(uuids) != len(set(uuids)):
            raise serializers.ValidationError('Duplicate keys found. ')
        return figures

    def validate_reviewers(self, revs):
        if User.objects.filter(id__in=revs).count() != len(revs):
            raise serializers.ValidationError('Reviewer does not exist.')
        return revs

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
                    fig_ser = NestedFigureSerializer()
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
                entry.figures.exclude(id__in=[each['id'] for each in figures if each.get('id')]).delete()
                # create if has no ids
                for each in figures:
                    if not each.get('id'):
                        fig_ser = NestedFigureSerializer()
                        fig_ser._validated_data = {**each, 'entry': entry}
                    else:
                        fig_ser = NestedFigureSerializer(
                            instance=Figure.objects.get(id=each['id']),
                            partial=True
                            )
                        fig_ser._validated_data = {**each, 'entry': entry}
                    fig_ser._errors = {}
                    fig_ser.save()
        else:
            entry = super().update(instance, validated_data)
        EntryReviewer.assign_creator(entry=entry,
                                     user=self.context['request'].user)
        return entry


class SourcePreviewSerializer(MetaInformationSerializerMixin,
                              serializers.ModelSerializer):
    class Meta:
        model = SourcePreview
        fields = '__all__'

    def create(self, validated_data):
        return SourcePreview.get_pdf(**validated_data)

    def update(self, instance, validated_data):
        return SourcePreview.get_pdf(**validated_data, instance=instance)
