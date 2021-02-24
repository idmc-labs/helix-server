import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import PageGraphqlPagination, DjangoObjectField

from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.entry.enums import RoleGrapheneEnum
from apps.report.models import Report
from apps.report.filters import ReportFilter
from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType


class ReportType(DjangoObjectType):
    class Meta:
        model = Report
        exclude_fields = ('reports', 'figures')

    figure_roles = graphene.List(graphene.NonNull(RoleGrapheneEnum))
    event_crisis_types = graphene.List(graphene.NonNull(CrisisTypeGrapheneEnum))


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
