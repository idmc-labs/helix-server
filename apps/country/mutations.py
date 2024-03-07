import graphene

from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker
from apps.contrib.mutations import ExportBaseMutation
from apps.contrib.models import ExcelDownload
from apps.country.schema import (
    SummaryType,
    ContextualAnalysisType,
)
from apps.country.filters import CountryFilterDataInputType
from apps.country.serializers import SummarySerializer, ContextualAnalysisSerializer
from apps.crisis.enums import CrisisTypeGrapheneEnum


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
    @permission_checker(['country.add_summary'])
    def mutate(root, info, data):
        serializer = SummarySerializer(data=data,
                                       context={'request': info.context.request})
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
    @permission_checker(['country.add_contextualanalysis'])
    def mutate(root, info, data):
        serializer = ContextualAnalysisSerializer(data=data,
                                                  context={'request': info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return CreateContextualAnalysis(errors=errors, ok=False)
        instance = serializer.save()
        return CreateContextualAnalysis(result=instance, errors=None, ok=True)


class ExportCountries(ExportBaseMutation):
    class Arguments(ExportBaseMutation.Arguments):
        filters = CountryFilterDataInputType(required=True)
    DOWNLOAD_TYPE = ExcelDownload.DOWNLOAD_TYPES.COUNTRY


class Mutation:
    create_summary = CreateSummary.Field()
    create_contextual_analysis = CreateContextualAnalysis.Field()
    export_countries = ExportCountries.Field()
