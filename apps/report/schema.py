import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField

from apps.country.schema import CountryType
from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.entry.enums import RoleGrapheneEnum
from apps.entry.schema import FigureListType
from apps.report.models import (
    Report,
    ReportComment,
    ReportApproval,
    ReportGeneration,
)
from apps.report.enums import ReportTypeEnum
from apps.report.filters import ReportFilter, CountryReportFilter
from apps.report.enums import ReportGenerationStatusEnum
from utils.graphene.types import CustomListObjectType, CustomDjangoListObjectType
from utils.graphene.fields import CustomPaginatedListObjectField, DjangoPaginatedListObjectField
from utils.pagination import PageGraphqlPaginationWithoutCount


class ReportCountryType(graphene.ObjectType):
    """
    Note: These fields are pre-defined in the queryset annotation
    """
    country = graphene.Field('apps.country.schema.CountryType', required=True)
    id = graphene.ID(required=True)
    total_stock_conflict = graphene.Int()
    total_flow_conflict = graphene.Int()
    total_stock_disaster = graphene.Int()
    total_flow_disaster = graphene.Int()

    def resolve_country(root, info, **kwargs):
        return root


class ReportCountryListType(CustomListObjectType):
    # TODO: lets reuse country list type now since both are the same
    class Meta:
        base_type = ReportCountryType
        filterset_class = CountryReportFilter


class ReportEventType(graphene.ObjectType):
    """
    NOTE: These fields are pre-defined in the queryset annotation
    """
    event = graphene.Field('apps.event.schema.EventType', required=True)
    id = graphene.ID(required=True)
    countries = graphene.List(graphene.NonNull(CountryType), required=False)
    total_stock_idp_figures = graphene.Field(graphene.Int)
    total_flow_nd_figures = graphene.Field(graphene.Int)

    def resolve_event(root, info, **kwargs):
        # FIXME: make me eventlist
        return root

    def resolve_countries(root, info, **kwargs):
        return root.countries.all()


class ReportEventListType(CustomListObjectType):
    class Meta:
        base_type = ReportEventType


class ReportEntryType(graphene.ObjectType):
    """
    NOTE: These fields are pre-defined in the queryset annotation
    """
    entry = graphene.Field('apps.entry.schema.EntryType', required=True)
    id = graphene.ID(required=True)
    is_reviewed = graphene.Boolean(required=True)
    is_under_review = graphene.Boolean(required=True)
    is_signed_off = graphene.Boolean(required=True)
    total_stock_idp_figures = graphene.Field(graphene.Int)
    total_flow_nd_figures = graphene.Field(graphene.Int)

    def resolve_entry(root, info, **kwargs):
        # FIXME: make me entrylist
        return root


class ReportEntryListType(CustomListObjectType):
    class Meta:
        base_type = ReportEntryType


class ReportCrisisType(graphene.ObjectType):
    """
    NOTE: These fields are pre-defined in the queryset annotation
    """
    crisis = graphene.Field('apps.crisis.schema.CrisisType', required=True)
    id = graphene.ID(required=True)
    total_stock_idp_figures = graphene.Field(graphene.Int)
    total_flow_nd_figures = graphene.Field(graphene.Int)

    def resolve_crisis(root, info, **kwargs):
        # FIXME: make me crisislist
        return root


class ReportCrisisListType(CustomListObjectType):
    class Meta:
        base_type = ReportCrisisType


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
        filter_fields = ()


class ReportApprovalType(DjangoObjectType):
    class Meta:
        model = ReportApproval


class ReportApprovalListType(CustomDjangoListObjectType):
    class Meta:
        model = ReportApproval
        filter_fields = ('is_approved',)


class ReportGenerationType(DjangoObjectType):
    class Meta:
        model = ReportGeneration
        exclude_fields = ('approvers', )

    status = graphene.NonNull(ReportGenerationStatusEnum)
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
        filter_fields = ('report',)


class ReportType(DjangoObjectType):
    class Meta:
        model = Report
        exclude_fields = ('reports', 'figures', 'masterfact_reports')

    comments = DjangoPaginatedListObjectField(ReportCommentListType,
                                              pagination=PageGraphqlPaginationWithoutCount(
                                                  page_size_query_param='pageSize'
                                              ))
    filter_figure_roles = graphene.List(graphene.NonNull(RoleGrapheneEnum))
    filter_event_crisis_types = graphene.List(graphene.NonNull(CrisisTypeGrapheneEnum))
    countries_report = CustomPaginatedListObjectField(ReportCountryListType,
                                                      accessor='countries_report',
                                                      pagination=PageGraphqlPaginationWithoutCount(
                                                          page_size_query_param='pageSize'
                                                      ))
    events_report = CustomPaginatedListObjectField(ReportEventListType,
                                                   accessor='events_report',
                                                   pagination=PageGraphqlPaginationWithoutCount(
                                                       page_size_query_param='pageSize'
                                                   ))
    entries_report = CustomPaginatedListObjectField(ReportEntryListType,
                                                    accessor='entries_report',
                                                    pagination=PageGraphqlPaginationWithoutCount(
                                                        page_size_query_param='pageSize'
                                                    ))
    figures_report = DjangoPaginatedListObjectField(FigureListType,
                                                    accessor='report_figures',
                                                    pagination=PageGraphqlPaginationWithoutCount(
                                                        page_size_query_param='pageSize'
                                                    ))
    crises_report = CustomPaginatedListObjectField(ReportCrisisListType,
                                                   accessor='crises_report',
                                                   pagination=PageGraphqlPaginationWithoutCount(
                                                       page_size_query_param='pageSize'
                                                   ))
    total_disaggregation = graphene.NonNull(ReportTotalsType)
    last_generation = graphene.Field(ReportGenerationType)
    generations = DjangoPaginatedListObjectField(
        ReportGenerationListType,
    )
    generated_from = graphene.Field(ReportTypeEnum)


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
