import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import PageGraphqlPagination, DjangoObjectField

from apps.country.models import Country
from apps.country.schema import CountryType
from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.crisis.models import Crisis
from apps.entry.enums import RoleGrapheneEnum
from apps.entry.models import Entry
from apps.event.models import Event
from apps.report.models import Report, ReportComment, ReportApproval
from apps.report.filters import ReportFilter, CountryReportFilter
from utils.graphene.types import CustomListObjectType, CustomDjangoListObjectType
from utils.graphene.fields import CustomPaginatedListObjectField, DjangoPaginatedListObjectField


class ReportFigureMixin:
    total_stock_conflict = graphene.Int()
    total_flow_conflict = graphene.Int()
    total_stock_disaster = graphene.Int()
    total_flow_disaster = graphene.Int()


class ReportCountryType(ReportFigureMixin, graphene.ObjectType):
    """
    Note: These fields are pre-defined in the queryset annotation
    """
    country = graphene.Field('apps.country.schema.CountryType', required=True)
    id = graphene.ID(required=True)
    name = graphene.String(required=True)

    def resolve_country(root, info, **kwargs):
        return Country.objects.get(id=root['id'])


class ReportCountryListType(CustomListObjectType):
    class Meta:
        base_type = ReportCountryType
        filterset_class = CountryReportFilter


class ReportEventType(ReportFigureMixin, graphene.ObjectType):
    """
    NOTE: These fields are pre-defined in the queryset annotation
    """
    event = graphene.Field('apps.event.schema.EventType', required=True)
    id = graphene.ID(required=True)
    name = graphene.String(required=True)
    event_type = graphene.Field(CrisisTypeGrapheneEnum, required=True)
    start_date = graphene.Date(required=True)
    countries = graphene.List(graphene.NonNull(CountryType), required=False)

    def resolve_event(root, info, **kwargs):
        return Event.objects.get(id=root['id'])

    def resolve_countries(root, info, **kwargs):
        return Event.objects.get(id=root['id']).countries.all()


class ReportEventListType(CustomListObjectType):
    class Meta:
        base_type = ReportEventType


class ReportEntryType(ReportFigureMixin, graphene.ObjectType):
    """
    NOTE: These fields are pre-defined in the queryset annotation
    """
    entry = graphene.Field('apps.entry.schema.EntryType', required=True)
    id = graphene.ID(required=True)
    article_title = graphene.String(required=True)
    created_at = graphene.Date(required=True)
    is_reviewed = graphene.Boolean(required=True)
    is_signed_off = graphene.Boolean(required=True)

    def resolve_entry(root, info, **kwargs):
        return Entry.objects.get(id=root['id'])


class ReportEntryListType(CustomListObjectType):
    class Meta:
        base_type = ReportEntryType


class ReportCrisisType(ReportFigureMixin, graphene.ObjectType):
    """
    NOTE: These fields are pre-defined in the queryset annotation
    """
    crisis = graphene.Field('apps.crisis.schema.CrisisType', required=True)
    id = graphene.ID(required=True)
    name = graphene.String(required=True)
    crisis_type = graphene.Field(CrisisTypeGrapheneEnum)

    def resolve_crisis(root, info, **kwargs):
        return Crisis.objects.get(id=root['id'])


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
        filter_fields = ()


class ReportType(DjangoObjectType):
    class Meta:
        model = Report
        exclude_fields = ('reports', 'figures', 'approvals', 'masterfactReports')

    comments = DjangoPaginatedListObjectField(ReportCommentListType,
                                              pagination=PageGraphqlPagination(
                                                  page_size_query_param='pageSize'
                                              ))
    figure_roles = graphene.List(graphene.NonNull(RoleGrapheneEnum))
    event_crisis_types = graphene.List(graphene.NonNull(CrisisTypeGrapheneEnum))
    countries_report = CustomPaginatedListObjectField(ReportCountryListType,
                                                      accessor='countries_report',
                                                      pagination=PageGraphqlPagination(
                                                          page_size_query_param='pageSize'
                                                      ))
    events_report = CustomPaginatedListObjectField(ReportEventListType,
                                                   accessor='events_report',
                                                   pagination=PageGraphqlPagination(
                                                       page_size_query_param='pageSize'
                                                   ))
    entries_report = CustomPaginatedListObjectField(ReportEntryListType,
                                                    accessor='entries_report',
                                                    pagination=PageGraphqlPagination(
                                                        page_size_query_param='pageSize'
                                                    ))
    crises_report = CustomPaginatedListObjectField(ReportCrisisListType,
                                                   accessor='crises_report',
                                                   pagination=PageGraphqlPagination(
                                                       page_size_query_param='pageSize'
                                                   ))
    total_disaggregation = graphene.NonNull(ReportTotalsType)
    approvers = DjangoPaginatedListObjectField(
        ReportApprovalListType,
        accessor='approvals',
        pagination=PageGraphqlPagination(
            page_size_query_param='pageSize'
        )
    )


class ReportListType(CustomDjangoListObjectType):
    class Meta:
        model = Report
        filterset_class = ReportFilter


class Query:
    report = DjangoObjectField(ReportType)
    report_list = DjangoPaginatedListObjectField(ReportListType,
                                                 pagination=PageGraphqlPagination(
                                                     page_size_query_param='pageSize'
                                                 ))
