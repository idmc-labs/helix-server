from rest_framework import serializers
from apps.country.models import Country
from .models import (
    Conflict, Disaster, GiddFigure, StatusLog, ReleaseMetadata,
    DisplacementData, PublicFigureAnalysis, IdpsSaddEstimate,
)
from apps.crisis.models import Crisis
from apps.entry.models import Figure


class CountrySerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source='idmc_short_name')

    class Meta:
        model = Country
        fields = (
            'iso2',
            'iso3',
            'country_name',
        )
        lookup_field = 'id'


class ConflictSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conflict
        fields = (
            'iso3',
            'country_name',
            'year',
            'new_displacement',
            'new_displacement_rounded',
            'total_displacement_rounded',
            'total_displacement',
        )
        lookup_field = 'id'


class DisasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disaster
        fields = (
            'iso3',
            'country_name',
            'year',
            'start_date',
            'start_date_accuracy',
            'end_date',
            'end_date_accuracy',
            'event_name',
            'new_displacement',
            'new_displacement_rounded',
            'total_displacement',
            'total_displacement_rounded',
            'hazard_category',
            'hazard_category_name',
            'hazard_sub_category',
            'hazard_sub_category_name',
            'hazard_type',
            'hazard_type_name',
            'hazard_sub_type',
            'hazard_sub_type_name',
            'event_codes',
            'event_codes_type',
        )
        lookup_field = 'id'


class DisplacementDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisplacementData
        fields = (
            'iso3',
            'country_name',
            'year',
            'conflict_new_displacement',
            'conflict_new_displacement_rounded',
            'conflict_total_displacement',
            'conflict_total_displacement_rounded',
            'disaster_new_displacement',
            'disaster_new_displacement_rounded',
            'disaster_total_displacement',
            'disaster_total_displacement_rounded',
        )


class PublicFigureAnalysisSerializer(serializers.ModelSerializer):
    figure_cause_name = serializers.SerializerMethodField('get_figure_cause_name')
    figure_category_name = serializers.SerializerMethodField('get_figure_category_name')

    def get_figure_cause_name(self, obj):
        return Crisis.CRISIS_TYPE.get(obj.figure_cause).label

    def get_figure_category_name(self, obj):
        return Figure.FIGURE_CATEGORY_TYPES.get(obj.figure_category).label

    class Meta:
        model = PublicFigureAnalysis
        fields = (
            'iso3',
            'year',
            'figure_cause',
            'figure_cause_name',
            'figure_category',
            'figure_category',
            'figure_category_name',
            'description',
            'figures',
            'figures_rounded',
            # TODO:
            # Add country_name
        )


class StatusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusLog
        fields = '__all__'


class ReleaseMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReleaseMetadata
        fields = ('pre_release_year', 'release_year')

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['modified_by'] = user
        return ReleaseMetadata.objects.create(**validated_data)


class DisaggregationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiddFigure
        fields = (
            'iso3',
            'figure',
            'country_name',
            'geographical_region_name',
            'year',
            'locations_coordinates',
            'unit',
            'category',
            'cause',
            'term',
            'total_figures',
            'household_size',
            'reported',
            'start_date',
            'end_date',
            'start_date_accuracy',
            'end_date_accuracy',
            'stock_date',
            'stock_date_accuracy',
            'stock_reporting_date',
            'sources',
            'publishers',
            'gidd_event',
            'is_housing_destruction',
            'locations_names',
            'locations_accuracy',
            'locations_type',
            'displacement_occurred',
        )


class IdpsSaddEstimateSerializer(serializers.ModelSerializer):
    """
    Serializer for validating and processing data from IdpsSaddEstimate CSV files.
    Automatically computes 'iso3' and 'country_name' from the associated country.
    """

    class Meta:
        model = IdpsSaddEstimate
        exclude = ['iso3', 'country_name']  # This are calculated by country

    def validate(self, validated_data):
        validated_data = super().validate(validated_data)
        country = validated_data['country']
        validated_data['country_name'] = country.name
        validated_data['iso3'] = country.iso3
        return validated_data
