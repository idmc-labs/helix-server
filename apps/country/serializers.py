from django.utils import timezone
from django.utils.translation import gettext
from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.country.models import ContextualAnalysis, HouseholdSize, HouseholdSizeCarryOverTask, Summary
from apps.users.models import User


class HouseholdSizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HouseholdSize
        fields = []


class CarryOverHouseholdSizeSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = HouseholdSizeCarryOverTask
        fields = []

    def validate_concurrent_copy(self, target_year) -> None:
        if (
            HouseholdSizeCarryOverTask.objects.filter(
                status__in=[
                    HouseholdSizeCarryOverTask.AHHS_CARRYOVER_OPERATION_STATUS.PENDING,
                    HouseholdSizeCarryOverTask.AHHS_CARRYOVER_OPERATION_STATUS.IN_PROGRESS,
                ]
            ).count()
            >= HouseholdSizeCarryOverTask.HOUSEHOLDSIZE_CONCURRENT_COPY_LIMIT
        ):
            raise serializers.ValidationError(
                gettext("Only %s ahhs copy(s) is allowed at a time")
                % HouseholdSizeCarryOverTask.HOUSEHOLDSIZE_CONCURRENT_COPY_LIMIT,
                code="limited-at-a-time",
            )

        if HouseholdSize.objects.filter(year=target_year).exists():
            raise serializers.ValidationError(gettext("Household size for year(=%s) already exists" % target_year))

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)

        # NOTE: we can't expect the target year from user
        # target_year must be timezone aware
        target_year = timezone.now().year

        self.validate_concurrent_copy(target_year=target_year)

        attrs["target_year"] = target_year

        return attrs

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.trigger_carry_over_household_size()

        return instance

    def update(self, instance, validated_data):
        raise serializers.ValidationError(gettext("manual modification of AHHS data is disabled"))


class SummarySerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Summary
        fields = "__all__"


class ContextualAnalysisSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ContextualAnalysis
        fields = "__all__"


class HouseholdSizeCliImportSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField()
    modified_at = serializers.DateTimeField()
    created_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    last_modified_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = HouseholdSize
        fields = "__all__"
