from django.utils.translation import gettext
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
    NOTE: An edit never updates an AHHS value in place. It archives the active value and inserts
    a new active one, the same as the update_ahhs command (see HouseholdSize.replace_active).
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

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is not None and not self.instance.is_active:
            raise serializers.ValidationError(gettext("Only the active household size can be edited."))
        return attrs

    def _save_new_value(self, country, year, data) -> HouseholdSize:
        active_records = list(HouseholdSize.objects.filter(country=country, year=year, is_active=True))
        # NOTE: Like update_ahhs, an edit that changes nothing doesn't create a new value
        if len(active_records) == 1 and active_records[0].has_same_data(data):
            return active_records[0]
        user = self.context["request"].user
        return HouseholdSize.replace_active(
            country=country,
            year=year,
            created_by=user,
            last_modified_by=user,
            **{field: data[field] for field in HouseholdSize.DATA_FIELDS if field in data},
        )

    def create(self, validated_data):
        return self._save_new_value(validated_data["country"], validated_data["year"], validated_data)

    def update(self, instance, validated_data):
        # NOTE: country and year identify the value being corrected, so they are kept from the instance
        data = {
            **{field: getattr(instance, field) for field in HouseholdSize.DATA_FIELDS},
            **{field: validated_data[field] for field in HouseholdSize.DATA_FIELDS if field in validated_data},
        }
        return self._save_new_value(instance.country, instance.year, data)


class HouseholdSizeCliImportSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField()
    modified_at = serializers.DateTimeField()
    created_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    last_modified_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = HouseholdSize
        fields = "__all__"
