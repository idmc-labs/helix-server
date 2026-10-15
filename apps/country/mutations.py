import graphene
from django.utils.translation import gettext

from apps.contrib.models import ExcelDownload
from apps.contrib.mutations import ExportBaseMutation
from apps.country.enums import HouseholdSizeGapFillingMethodEnum
from apps.country.filters import (
    CountryFilterDataInputType,
    HouseholdSizeFilterDataTypeInputType,
    MonitoringSubRegionFilterDataInputType,
)
from apps.country.models import HouseholdSize
from apps.country.schema import (
    ContextualAnalysisType,
    CountryHouseholdSizeType,
    SummaryType,
)
from apps.country.serializers import (
    ContextualAnalysisSerializer,
    HouseholdSizeSerializer,
    SummarySerializer,
)
from apps.crisis.enums import CrisisTypeGrapheneEnum
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker


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


class HouseholdSizeCreateInputType(graphene.InputObjectType):
    """
    Household Size Create InputType
    """

    country = graphene.ID(required=True)
    year = graphene.Int(required=True)
    size = graphene.Float(required=True)
    data_source_category = graphene.String(required=True)
    source = graphene.String(required=True)
    source_link = graphene.String()
    notes = graphene.String()
    is_active = graphene.Boolean()
    reference_date = graphene.Date()
    gap_filling_method = graphene.Field(HouseholdSizeGapFillingMethodEnum)


class HouseholdSizeUpdateInputType(graphene.InputObjectType):
    """
    Household Size Update InputType
    """

    id = graphene.ID(required=True)
    country = graphene.ID()
    year = graphene.Int()
    size = graphene.Float()
    data_source_category = graphene.String()
    source = graphene.String()
    source_link = graphene.String()
    notes = graphene.String()
    is_active = graphene.Boolean()
    reference_date = graphene.Date()
    gap_filling_method = graphene.Field(HouseholdSizeGapFillingMethodEnum)


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


class CreateHouseholdSize(graphene.Mutation):
    class Arguments:
        data = HouseholdSizeCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(CountryHouseholdSizeType)

    @staticmethod
    @permission_checker(["country.add_householdsize"])
    def mutate(root, info, data):
        serializer = HouseholdSizeSerializer(data=data, context={"request": info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return CreateHouseholdSize(errors=errors, ok=False)
        instance = serializer.save()
        return CreateHouseholdSize(result=instance, errors=None, ok=True)


class UpdateHouseholdSize(graphene.Mutation):
    class Arguments:
        data = HouseholdSizeUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(CountryHouseholdSizeType)

    @staticmethod
    @permission_checker(["country.change_householdsize"])
    def mutate(root, info, data):
        try:
            instance = HouseholdSize.objects.get(id=data["id"])
        except HouseholdSize.DoesNotExist:
            return UpdateHouseholdSize(
                errors=[dict(field="nonFieldErrors", messages=gettext("Household size does not exist."))]
            )
        serializer = HouseholdSizeSerializer(
            instance=instance, data=data, partial=True, context={"request": info.context.request}
        )
        if errors := mutation_is_not_valid(serializer):
            return UpdateHouseholdSize(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateHouseholdSize(result=instance, errors=None, ok=True)


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


class Mutation:
    create_summary = CreateSummary.Field()
    create_contextual_analysis = CreateContextualAnalysis.Field()
    create_household_size = CreateHouseholdSize.Field()
    update_household_size = UpdateHouseholdSize.Field()
    export_countries = ExportCountries.Field()
    export_monitoring_sub_regions = ExportMonitoringSubRegions.Field()
    export_household_size = ExportHouseholdSize.Field()
