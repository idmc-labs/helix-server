from django_filters import rest_framework as df
import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import PageGraphqlPagination, DjangoObjectField

from apps.country.models import Country
from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.entry.enums import RoleGrapheneEnum
from apps.report.models import Report
from apps.report.filters import ReportFilter, CountryReportFilter
from utils.fields import (
    DjangoPaginatedListObjectField,
    CustomDjangoListObjectType,
    CustomListObjectType,
    CustomPaginatedListObjectField,
)


class ReportCountryType(graphene.ObjectType):
    """
    Note: These fields are pre-defined in the queryset annotation
    """
    country = graphene.Field('apps.country.schema.CountryType', required=True)
    total_stock_conflict = graphene.Int()
    total_flow_conflict = graphene.Int()
    total_stock_disaster = graphene.Int()
    total_flow_disaster = graphene.Int()

    def resolve_country(root, info, **kwargs):
        return Country.objects.get(id=root['country'])


class ReportCountryListType(CustomListObjectType):
    class Meta:
        base_type = ReportCountryType
        filterset_class = CountryReportFilter


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
