from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.country.models import ContextualAnalysis, HouseholdSize, Summary
from apps.users.models import User


class SummarySerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Summary
        fields = "__all__"


class ContextualAnalysisSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ContextualAnalysis
        fields = "__all__"
        extra_kwargs = {"crisis_type": {"required": True}, "update": {"required": True}}


class HouseholdSizeSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    """
    Household size is never updated directly. If the country and year already have an active value,
    the old value is archived and a new active value is created (see HouseholdSize.replace_active).
    """

    class Meta:
        model = HouseholdSize
        fields = (
            "id",
            "country",
            "year",
            *HouseholdSize.DATA_FIELDS,
            "is_active",
            "created_at",
            "modified_at",
            "created_by",
            "last_modified_by",
        )
        read_only_fields = ("is_active",)

    def create(self, validated_data):
        country = validated_data["country"]
        year = validated_data["year"]
        active_records = list(HouseholdSize.objects.filter(country=country, year=year, is_active=True).order_by("-id"))
        latest_active_record = None
        if active_records:
            latest_active_record = active_records[0]

        # If there is already an active value, this is a correction of it.
        # So the fields that are not sent keep the value of the active record.
        data = {}
        for field in HouseholdSize.DATA_FIELDS:
            if field in validated_data:
                data[field] = validated_data[field]
            elif latest_active_record:
                data[field] = getattr(latest_active_record, field)

        # Same as update_ahhs, don't create a new value if nothing has changed
        if len(active_records) == 1 and latest_active_record.has_same_data(data):
            return latest_active_record

        user = self.context["request"].user
        return HouseholdSize.replace_active(
            country=country,
            year=year,
            created_by=user,
            last_modified_by=user,
            **data,
        )


class HouseholdSizeCliImportSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField()
    modified_at = serializers.DateTimeField()
    created_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    last_modified_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = HouseholdSize
        fields = "__all__"
