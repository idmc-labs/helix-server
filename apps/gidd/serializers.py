from rest_framework import serializers
from apps.country.models import Country
from .models import (
    Conflict, Disaster, GiddFigure, StatusLog, ReleaseMetadata,
    DisplacementData, PublicFigureAnalysis, IdpsSaddEstimate,
)
from apps.crisis.models import Crisis
from apps.entry.models import Figure


class CountrySerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(
        source='idmc_short_name',
        help_text="Short name of the country or territory."
    )

    iso3 = serializers.CharField(
        help_text="Represents the ISO 3166-1 alpha-3 code. "
        "The code 'AB9' is assigned to the Abyei Area."
    )

    class Meta:
        model = Country
        fields = (
            'iso2',
            'iso3',
            'country_name',
        )
        lookup_field = 'id'


class ConflictSerializer(serializers.ModelSerializer):
    iso3 = serializers.CharField(
        help_text="Represents the ISO 3166-1 alpha-3 code. "
        "The code 'AB9' is assigned to the Abyei Area."
    )

    country_name = serializers.CharField(
        help_text="Short name of the country or territory."
    )

    year = serializers.IntegerField(
        help_text="Indicates the year for which displacement data are reported."
    )

    new_displacement_rounded = serializers.IntegerField(
        help_text="Total number of internal displacements reported "
        "\"(rounded figures at national level)\" as a result of conflict "
        "and violence over the reporting year. Units are recorded as 'internal displacement flows'."
    )

    new_displacement = serializers.IntegerField(
        help_text="Total number of internal displacements reported "
        "\"(not rounded)\" as a result of conflict and violence over the "
        "reporting year. Units are recorded as 'internal displacement flows'."
    )

    total_displacement_rounded = serializers.IntegerField(
        help_text="Total number of IDPs \"(rounded figures at the national level)\" "
        "as a result of conflict and violence as of the end of the reporting year. "
        "Units are recorded as 'People'."
    )

    total_displacement = serializers.IntegerField(
        help_text="Total number of IDPs \"(not rounded)\" "
        "as a result of conflict and violence as of the end of the reporting year."
        "Units are recorded as 'People'."
    )

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
    iso3 = serializers.CharField(
        help_text="Represents the ISO 3166-1 alpha-3 code. "
        "The code 'AB9' is assigned to the Abyei Area."
    )

    country_name = serializers.CharField(
        help_text="Short name of the country or territory."
    )

    year = serializers.IntegerField(
        help_text="Indicates the year for which displacement data are reported."
    )

    event_name = serializers.CharField(
        help_text="Common or official event name for the event if available. "
        "Otherwise events are coded based on the country type of hazard location and event start date."
    )

    hazard_category_name = serializers.CharField(
        help_text="Hazard category based on the CRED EM-DAT classification."
    )

    hazard_type_name = serializers.CharField(
        help_text="Hazard type as categorized by CRED EM-DAT."
    )

    hazard_sub_type_name = serializers.CharField(
        help_text="Specific sub-type of the hazard based on the CRED EM-DAT classification."
    )

    new_displacement = serializers.IntegerField(
        help_text="Total number of internal displacements reported \"(not rounded)\" "
        "as a result of disasters over the reporting year. "
        "Units are recorded as 'internal displacement flows' or 'internal displacement movements.'"
    )

    new_displacement_rounded = serializers.IntegerField(
        help_text="Total number of internal displacements reported "
        "\"(rounded figures at national level)\" as a result of disasters "
        "over the reporting year. Units are recorded as 'internal displacement flows' or 'internal displacement movements.'"
    )

    event_codes = serializers.ListField(
        child=serializers.CharField(),
        help_text="Unique codes such as the GLIDE number and "
        "other database-specific codes used to identify "
        "and track specific events across various databases."
    )
    start_date = serializers.DateField(
        help_text="Approximated start date of the event."
    )
    end_date = serializers.DateField(
        help_text="Approximated end date of the event."
    )
    start_date_accuracy = serializers.CharField(
        help_text="This field describes the potential timeframe within which "
        "the event likely occurred. The values indicate the period around the date."
    )
    end_date_accuracy = serializers.CharField(
        help_text="This field describes the potential timeframe within which "
        "the event likely ended. The values indicate the period around the date."
    )

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
    iso3 = serializers.CharField(
        help_text="Represents the ISO 3166-1 alpha-3 code. "
        "The code 'AB9' is assigned to the Abyei Area."
    )

    country_name = serializers.CharField(
        help_text="Short name of the country or territory."
    )

    year = serializers.IntegerField(
        help_text="Indicates the year for which displacement data are reported."
    )

    conflict_total_displacement_rounded = serializers.IntegerField(
        help_text="Total number of IDPs \"(rounded figures at the national level)\" "
        "as a result of conflict and violence as of the end of the reporting year. "
        "Units are recorded as 'People'."
    )

    conflict_total_displacement = serializers.IntegerField(
        help_text="Total number of IDPs \"(not rounded)\" "
        "as a result of conflict and violence as of the end of the reporting year."
        "Units are recorded as 'People'."
    )

    conflict_new_displacement_rounded = serializers.IntegerField(
        help_text="Total number of internal displacements reported "
        "\"(rounded figures at national level)\" as a result of conflict "
        "and violence over the reporting year. Units are recorded as 'internal displacement flows'."
    )

    conflict_new_displacement = serializers.IntegerField(
        help_text="Total number of internal displacements reported "
        "\"(not rounded)\" as a result of conflict and violence over the "
        "reporting year. Units are recorded as 'internal displacement flows'."
    )

    disaster_new_displacement_rounded = serializers.IntegerField(
        help_text="Total number of internal displacements reported "
        "\"(rounded figures at national level)\" as a result of disasters over the reporting year. "
        "Units are recorded as 'internal displacement flows'."
    )

    disaster_new_displacement = serializers.IntegerField(
        help_text="Total number of internal displacements reported \"(not rounded)\" as a "
        "result of disasters over the reporting year. "
        "Units are recorded as 'internal displacement flows'."
    )

    disaster_total_displacement_rounded = serializers.IntegerField(
        help_text="Total number of IDPs \"(rounded figures at national level)\" as a "
        "result of disasters as of the end of the reporting year. "
        "Units are recorded as 'People'."
    )

    disaster_total_displacement = serializers.IntegerField(
        help_text="Total number of IDPs \"(not rounded)\" as a result"
        "of disasters as of the end of the reporting year. Units are recorded as 'People'."
    )

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
    figure_cause_name = serializers.SerializerMethodField(
        'get_figure_cause_name',
        help_text="Identifies the trigger of displacement such as conflict or disasters."
    )
    figure_category_name = serializers.SerializerMethodField(
        'get_figure_category_name',
        help_text="Categorizes the type of displacement metric. "
        "It details values for \"Internal Displacements\" (internal displacement flows) "
        "and Total Number of IDPs, \"Total number of IDPs\" as defined earlier in this document"
    )
    year = serializers.IntegerField(
        help_text="Indicates the year for which displacement data are reported."
    )
    iso3 = serializers.CharField(
        help_text="Represents the ISO 3166-1 alpha-3 code. The code 'AB9' is assigned to the Abyei Area."
    )
    figures_rounded = serializers.IntegerField(
        help_text="Displays rounded figures to provide a simplified view of the data "
        "that matches the figures reported in the Global Report on Internal Displacement (GRID)."
    )
    description = serializers.CharField(
        help_text="Provides contextual information about the data including sources and data limitations. "
        "It is essential for representing the analysis conducted by IDMC analysts. "
        "This field also details the methodology used, descriptions of sources,"
        "and outlines any caveats and challenges identified with the displacement figures reported."
    )
    figures = serializers.IntegerField(
        help_text="Represents the total number of internal displacements or IDPs. "
        "For internal displacements, units are recorded as 'internal displacement flows' "
        "or 'internal displacement movements.' For the total number of IDPs, units reflect "
        "the total number of people living in displacement."
    )

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
            'figure_raw_id',
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
        validated_data['country_name'] = country.idmc_short_name
        validated_data['iso3'] = country.iso3
        return validated_data
