import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField
from utils.graphene.enums import EnumDescription

from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.entry.enums import (
    RoleGrapheneEnum,
    FigureTermsEnum,
    FigureCategoryTypeEnum,
    FigureReviewStatusEnum,
)
from apps.report.models import (
    Report,
    ReportComment,
    ReportApproval,
    ReportGeneration,
)
from apps.report.enums import ReportTypeEnum
from apps.report.filters import (
    ReportFilter,
    ReportApprovalFilter,
    ReportGenerationFilter,
    ReportCommentFilter,
)
from apps.report.enums import ReportGenerationStatusEnum
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.pagination import PageGraphqlPaginationWithoutCount


class ReportTotalsType(graphene.ObjectType):
    total_stock_conflict_sum = graphene.Int()
    total_flow_conflict_sum = graphene.Int()
    total_stock_disaster_sum = graphene.Int()
    total_flow_disaster_sum = graphene.Int()


class ReportCommentType(DjangoObjectType):
    class Meta:
        model = ReportComment


class ReportCommentListType(CustomDjangoListObjectType):
    class Meta:
        model = ReportComment
        filterset_class = ReportCommentFilter


class ReportApprovalType(DjangoObjectType):
    class Meta:
        model = ReportApproval


class ReportApprovalListType(CustomDjangoListObjectType):
    class Meta:
        model = ReportApproval
        filterset_class = ReportApprovalFilter


class ReportGenerationType(DjangoObjectType):
    class Meta:
        model = ReportGeneration
        exclude_fields = ('approvers', )

    status = graphene.NonNull(ReportGenerationStatusEnum)
    status_display = EnumDescription(source='get_status_display')
    is_approved = graphene.Boolean()
    approvals = DjangoPaginatedListObjectField(
        ReportApprovalListType,
    )

    def resolve_full_report(root, info, **kwargs):
        if root.status == ReportGeneration.REPORT_GENERATION_STATUS.COMPLETED:
            return info.context.request.build_absolute_uri(root.full_report.url)
        return None

    def resolve_snapshot(root, info, **kwargs):
        if root.status == ReportGeneration.REPORT_GENERATION_STATUS.COMPLETED:
            return info.context.request.build_absolute_uri(root.snapshot.url)
        return None


class ReportGenerationListType(CustomDjangoListObjectType):
    class Meta:
        model = ReportGeneration
        filterset_class = ReportGenerationFilter


class ReportType(DjangoObjectType):
    class Meta:
        model = Report
        exclude_fields = ('reports', 'figures', 'masterfact_reports')

    comments = DjangoPaginatedListObjectField(ReportCommentListType,
                                              pagination=PageGraphqlPaginationWithoutCount(
                                                  page_size_query_param='pageSize'
                                              ))

    # NOTE: We need to define this at ExtractionQueryObjectType as well
    filter_figure_roles = graphene.List(graphene.NonNull(RoleGrapheneEnum))
    filter_figure_roles_display = EnumDescription(source='get_filter_figure_roles_display')
    filter_figure_crisis_types = graphene.List(graphene.NonNull(CrisisTypeGrapheneEnum))
    filter_figure_crisis_types_display = EnumDescription(source='get_filter_figure_crisis_types_display')
    filter_figure_categories = graphene.List(graphene.NonNull(FigureCategoryTypeEnum))
    filter_figure_terms = graphene.List(graphene.NonNull(FigureTermsEnum))
    filter_figure_terms_display = EnumDescription(source='get_filter_figure_terms_display')
    filter_figure_review_status = graphene.List(graphene.NonNull(FigureReviewStatusEnum))

    total_disaggregation = graphene.NonNull(ReportTotalsType)
    # FIXME: use dataloader for last_generation
    last_generation = graphene.Field(ReportGenerationType)
    generations = DjangoPaginatedListObjectField(
        ReportGenerationListType,
    )
    generated_from = graphene.Field(ReportTypeEnum)
    generated_from_display = EnumDescription(source='get_generated_from_display_display')


class ReportListType(CustomDjangoListObjectType):
    class Meta:
        model = Report
        filterset_class = ReportFilter


class Query:
    generation = DjangoObjectField(ReportGenerationType)

    report = DjangoObjectField(ReportType)
    report_list = DjangoPaginatedListObjectField(ReportListType,
                                                 pagination=PageGraphqlPaginationWithoutCount(
                                                     page_size_query_param='pageSize'
                                                 ))
    report_comment = DjangoObjectField(ReportCommentType)
    report_comment_list = DjangoPaginatedListObjectField(ReportCommentListType,
                                                         pagination=PageGraphqlPaginationWithoutCount(
                                                             page_size_query_param='pageSize'
                                                         ))
    report_generation = DjangoObjectField(ReportGenerationType)
    report_generation_list = DjangoPaginatedListObjectField(ReportGenerationListType,
                                                            pagination=PageGraphqlPaginationWithoutCount(
                                                                page_size_query_param='pageSize'
                                                            ))
