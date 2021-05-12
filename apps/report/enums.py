__all__ = ['ReportGenerationStatusEnum']

import graphene

from apps.report.models import ReportGeneration, Report

from utils.enums import enum_description

ReportGenerationStatusEnum = graphene.Enum.from_enum(ReportGeneration.REPORT_GENERATION_STATUS, description=enum_description)
ReportTypeEnum = graphene.Enum.from_enum(Report.REPORT_TYPE, description=enum_description)
ReportReviewFilterEnum = graphene.Enum.from_enum(Report.REPORT_REVIEW_FILTER, description=enum_description)

enum_map = dict(
    REPORT_GENERATION_STATUS=ReportGenerationStatusEnum,
    REPORT_TYPE=ReportTypeEnum,
    REPORT_REVIEW_FILTER=ReportReviewFilterEnum,
)


class ReportEnumType(graphene.ObjectType):
    review_filter = graphene.Field(ReportReviewFilterEnum)
