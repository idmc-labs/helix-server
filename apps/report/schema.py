import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import PageGraphqlPagination, DjangoObjectField

from apps.country.models import Country
from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.entry.enums import RoleGrapheneEnum
from apps.report.models import Report
from apps.report.filters import ReportFilter
from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType


class ReportCountryType(graphene.ObjectType):
    country = graphene.Field('apps.country.schema.CountryType', required=True)
    total_stock_conflict = graphene.Int()
    total_flow_conflict = graphene.Int()
    total_stock_disaster = graphene.Int()
    total_flow_disaster = graphene.Int()

    def resolve_country(root, info, **kwargs):
        return Country.objects.get(id=root['country'])


class ReportType(DjangoObjectType):
    class Meta:
        model = Report
        exclude_fields = ('reports', 'figures')

    figure_roles = graphene.List(graphene.NonNull(RoleGrapheneEnum))
    event_crisis_types = graphene.List(graphene.NonNull(CrisisTypeGrapheneEnum))
    countries_report = graphene.List(ReportCountryType)


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
