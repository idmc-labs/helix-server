from django.db import transaction
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
    class Meta:
        model = HouseholdSize
        fields = (
            "id",
            "country",
            "year",
            "size",
            "data_source_category",
            "source",
            "source_link",
            "notes",
            "is_active",
            "reference_date",
            "gap_filling_method",
            "created_at",
            "modified_at",
            "created_by",
            "last_modified_by",
        )

    @transaction.atomic
    def create(self, validated_data):
        if validated_data.get("is_active"):
            # NOTE: Only one active household size is allowed per country-year
            HouseholdSize.objects.filter(
                country=validated_data["country"],
                year=validated_data["year"],
                is_active=True,
            ).update(is_active=False)
        return super().create(validated_data)


class HouseholdSizeCliImportSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField()
    modified_at = serializers.DateTimeField()
    created_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    last_modified_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = HouseholdSize
        fields = "__all__"
