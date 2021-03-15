__all__ = ['ReportGenerationStatusEnum']

import graphene

from apps.report.models import ReportGeneration

from utils.enums import enum_description

ReportGenerationStatusEnum = graphene.Enum.from_enum(ReportGeneration.REPORT_GENERATION_STATUS, description=enum_description)

enum_map = dict(
    REPORT_GENERATION_STATUS=ReportGenerationStatusEnum
)
