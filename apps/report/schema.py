import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import PageGraphqlPagination, DjangoObjectField

from apps.country.models import Country
from apps.country.schema import CountryType
from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.entry.enums import RoleGrapheneEnum
from apps.event.models import Event
from apps.report.models import Report
from apps.report.filters import ReportFilter, CountryReportFilter
from utils.graphene.types import CustomListObjectType, CustomDjangoListObjectType
from utils.graphene.fields import CustomPaginatedListObjectField, DjangoPaginatedListObjectField


class ReportCountryType(graphene.ObjectType):
    """
    Note: These fields are pre-defined in the queryset annotation
    """
    country = graphene.Field('apps.country.schema.CountryType', required=True)
    id = graphene.ID(required=True)
    name = graphene.String(required=True)
    total_stock_conflict = graphene.Int()
    total_flow_conflict = graphene.Int()
    total_stock_disaster = graphene.Int()
    total_flow_disaster = graphene.Int()

    def resolve_country(root, info, **kwargs):
        return Country.objects.get(id=root['id'])


class ReportCountryListType(CustomListObjectType):
    class Meta:
        base_type = ReportCountryType
        filterset_class = CountryReportFilter


class ReportEventType(graphene.ObjectType):
    """
    NOTE: These fields are pre-defined in the queryset annotation
    """
    event = graphene.Field('apps.event.schema.EventType', required=True)
    id = graphene.ID(required=True)
    name = graphene.String(required=True)
    event_type = graphene.Field(CrisisTypeGrapheneEnum, required=True)
    start_date = graphene.Date(required=True)
    countries = graphene.List(graphene.NonNull(CountryType), required=False)
    total_stock_conflict = graphene.Int()
    total_flow_conflict = graphene.Int()
    total_stock_disaster = graphene.Int()
    total_flow_disaster = graphene.Int()

    def resolve_event(root, info, **kwargs):
        return Event.objects.get(id=root['id'])

    def resolve_event_type(root, info, **kwargs):
        return Event.objects.get(id=root['id']).event_type

    def resolve_start_date(root, info, **kwargs):
        return Event.objects.get(id=root['id']).start_date

    def resolve_countries(root, info, **kwargs):
        return Event.objects.get(id=root['id']).countries.all()


class ReportEventListType(CustomListObjectType):
    class Meta:
        base_type = ReportEventType


class ReportType(DjangoObjectType):
    class Meta:
        model = Report
        exclude_fields = ('reports', 'figures')

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
