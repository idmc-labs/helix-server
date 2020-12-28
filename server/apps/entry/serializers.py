from django.core.validators import MinValueValidator
from collections import OrderedDict

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext, gettext_lazy as _
from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.entry.models import Entry, Figure, SourcePreview, OSMName, EntryReviewer
from apps.users.models import User
from apps.users.enums import USER_ROLE


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
    id = serializers.IntegerField(required=False)

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
            raise serializers.ValidationError(
                gettext('Make sure the dates are unique in a figure. '))
        return strata

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        errors = OrderedDict()
        errors.update(Figure.clean_idu(attrs, self.instance))
        if errors:
            raise ValidationError(errors)
        return attrs

    def create(self, validated_data: dict) -> Figure:
        geo_locations = validated_data.pop('geo_locations', [])
        if geo_locations:
            geo_locations = OSMName.objects.bulk_create(
                [OSMName(**each) for each in geo_locations]
            )
        instance = Figure.objects.create(**validated_data)
        instance.geo_locations.set(geo_locations)
        return instance


class FigureSerializer(MetaInformationSerializerMixin,
                       CommonFigureValidationMixin,
                       serializers.ModelSerializer):
    age_json = DisaggregatedAgeSerializer(many=True, required=False)
    strata_json = DisaggregatedStratumSerializer(many=True, required=False)
    geo_locations = OSMNameSerializer(many=True, required=False)

    class Meta:
        model = Figure
        fields = '__all__'


class NestedFigureSerializer(MetaInformationSerializerMixin,
                             CommonFigureValidationMixin,
                             serializers.ModelSerializer):
    age_json = DisaggregatedAgeSerializer(many=True, required=False)
    strata_json = DisaggregatedStratumSerializer(many=True, required=False)
    geo_locations = OSMNameSerializer(many=True, required=False)
    # to allow updating
    id = serializers.IntegerField(required=False)
    uuid = serializers.CharField(required=False)

    class Meta:
        model = Figure
        exclude = ('entry',)

    def _validate_geo_locations(self, geo_locations) -> list:
        if self.instance:
            if {each['id'] for each in geo_locations if 'id' in each}.difference(
                list(self.instance.geo_locations.values_list('id', flat=True))
            ):
                raise serializers.ValidationError(
                    dict(geo_locations='Some geo locations not found.')
                )
        return geo_locations

    def validate(self, attrs) -> dict:
        # manually call validate by setting the instance
        if not self.instance and attrs.get('id'):
            self.instance = Figure.objects.get(id=attrs['id'])
        self._validate_geo_locations(attrs.get('geo_locations', []))
        return attrs

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


class EntrySerializer(MetaInformationSerializerMixin,
                      serializers.ModelSerializer):
    figures = NestedFigureSerializer(many=True, required=False)
    reviewers = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.exclude(
            groups__name=USER_ROLE.GUEST.name
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
                entry.figures.exclude(
                    id__in=[each['id'] for each in figures if each.get('id')]).delete()
                # create if has no ids
                for each in figures:
                    if not each.get('id'):
                        fig_ser = NestedFigureSerializer()
                        fig_ser._validated_data = {**each, 'entry': entry}
                    else:
                        fig_ser = NestedFigureSerializer(
                            instance=entry.figures.get(id=each['id']),
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
