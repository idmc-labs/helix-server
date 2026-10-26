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
    NOTE: AHHS values are never updated in place. Saving a value for a country-year that already has
    an active value archives it and inserts a new active one, the same as the update_ahhs command
    (see HouseholdSize.replace_active).
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
        archive_notes = None
        data = {field: validated_data[field] for field in HouseholdSize.DATA_FIELDS if field in validated_data}
        if active_records:
            # NOTE: A value for a country-year with an active value is a correction of it. Notes is the
            # reason for the correction and is saved on the archived value, the new value keeps the
            # notes of the value it replaces, and fields that are not sent keep the active value.
            archive_notes = data.pop("notes", None)
            data = {
                **{field: getattr(active_records[0], field) for field in HouseholdSize.DATA_FIELDS},
                **data,
            }
        # NOTE: Like update_ahhs, a correction that changes nothing doesn't create a new value
        if len(active_records) == 1 and active_records[0].has_same_data(data):
            return active_records[0]
        user = self.context["request"].user
        return HouseholdSize.replace_active(
            country=country,
            year=year,
            created_by=user,
            last_modified_by=user,
            archive_notes=archive_notes,
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
