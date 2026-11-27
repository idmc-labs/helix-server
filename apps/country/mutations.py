import graphene
from django.db import transaction
from django.utils.translation import gettext

from apps.contrib.models import ExcelDownload
from apps.contrib.mutations import ExportBaseMutation
from apps.country.filters import (
    CountryFilterDataInputType,
    HouseholdSizeFilterDataTypeInputType,
    MonitoringSubRegionFilterDataInputType,
)
from apps.country.schema import ContextualAnalysisType, SummaryType
from apps.country.serializers import ContextualAnalysisSerializer, SummarySerializer
from apps.country.tasks import carry_over_ahhs_data
from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.gidd.models import StatusLog
from apps.gidd.serializers import StatusLogSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import is_authenticated, permission_checker


class SummaryCreateInputType(graphene.InputObjectType):
    """
    Crisis Create InputType
    """

    summary = graphene.String(required=True)
    country = graphene.ID(required=True)


class ContextualAnalysisCreateInputType(graphene.InputObjectType):
    """
    Crisis Create InputType
    """

    update = graphene.String(required=True)
    country = graphene.ID(required=True)
    publish_date = graphene.Date()
    crisis_type = graphene.NonNull(CrisisTypeGrapheneEnum)


class CreateSummary(graphene.Mutation):
    class Arguments:
        data = SummaryCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(SummaryType)

    @staticmethod
    @permission_checker(["country.add_summary"])
    def mutate(root, info, data):
        serializer = SummarySerializer(data=data, context={"request": info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return CreateSummary(errors=errors, ok=False)
        instance = serializer.save()
        return CreateSummary(result=instance, errors=None, ok=True)


class CreateContextualAnalysis(graphene.Mutation):
    class Arguments:
        data = ContextualAnalysisCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ContextualAnalysisType)

    @staticmethod
    @permission_checker(["country.add_contextualanalysis"])
    def mutate(root, info, data):
        serializer = ContextualAnalysisSerializer(data=data, context={"request": info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return CreateContextualAnalysis(errors=errors, ok=False)
        instance = serializer.save()
        return CreateContextualAnalysis(result=instance, errors=None, ok=True)


class ExportCountries(ExportBaseMutation):
    class Arguments(ExportBaseMutation.Arguments):
        filters = CountryFilterDataInputType(required=True)

    DOWNLOAD_TYPE = ExcelDownload.DOWNLOAD_TYPES.COUNTRY


class ExportMonitoringSubRegions(ExportBaseMutation):
    class Arguments(ExportBaseMutation.Arguments):
        filters = MonitoringSubRegionFilterDataInputType(required=True)

    DOWNLOAD_TYPE = ExcelDownload.DOWNLOAD_TYPES.MONITORING_SUB_REGION


class ExportHouseholdSize(ExportBaseMutation):
    class Arguments(ExportBaseMutation.Arguments):
        filters = HouseholdSizeFilterDataTypeInputType(required=True)

    DOWNLOAD_TYPE = ExcelDownload.DOWNLOAD_TYPES.AHHS


class CarryOverHouseholdSize(graphene.Mutation):
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(SummaryType)

    @staticmethod
    @is_authenticated()
    # @permission_checker(["gidd.update_gidd_data_gidd"])
    def mutate(root, info):
        user = info.context.user
        # Check if any pending updates
        status_log = StatusLog.objects.last()
        if status_log and status_log.status == StatusLog.Status.PENDING:
            return CarryOverHouseholdSize(
                errors=[
                    dict(
                        field="nonFieldErrors",
                        messages=gettext("Carry over household data in background"),
                    )
                ],
                ok=False,
            )

        serializer = StatusLogSerializer(data=dict(triggered_by=user.id))
        if errors := mutation_is_not_valid(serializer):
            return CarryOverHouseholdSize(errors=errors, ok=False)
        instance = serializer.save()
        # Update date in background
        transaction.on_commit(lambda: carry_over_ahhs_data.delay(log_id=instance.id))
        return CarryOverHouseholdSize(result=instance, errors=None, ok=True)


class Mutation:
    create_summary = CreateSummary.Field()
    create_contextual_analysis = CreateContextualAnalysis.Field()
    export_countries = ExportCountries.Field()
    export_monitoring_sub_regions = ExportMonitoringSubRegions.Field()
    export_household_size = ExportHouseholdSize.Field()
    carry_over_household_size = CarryOverHouseholdSize.Field()
