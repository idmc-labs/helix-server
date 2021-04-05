import graphene
from graphene_django.filter.utils import get_filtering_args_from_filterset

from apps.country.schema import (
    CountryType,
    SummaryType,
    ContextualAnalysisType,
)
from apps.country.filters import CountryFilter
from apps.country.serializers import SummarySerializer, ContextualAnalysisSerializer
from apps.contrib.serializers import ExcelDownloadSerializer
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


class ExportCountries(graphene.Mutation):
    class Meta:
        arguments = get_filtering_args_from_filterset(
            CountryFilter,
            CountryType
        )

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, **kwargs):
        from apps.contrib.models import ExcelDownload

        serializer = ExcelDownloadSerializer(
            data=dict(
                download_type=int(ExcelDownload.DOWNLOAD_TYPES.COUNTRY),
                filters=kwargs,
            ),
            context=dict(request=info.context)
        )
        if errors := mutation_is_not_valid(serializer):
            return ExportCountries(errors=errors, ok=False)
        serializer.save()
        return ExportCountries(errors=None, ok=True)


class Mutation:
    create_summary = CreateSummary.Field()
    create_contextual_analysis = CreateContextualAnalysis.Field()
    export_countries = ExportCountries.Field()
