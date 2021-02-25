import graphene
from django.utils.translation import gettext

from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.report.models import Report
from apps.report.schema import ReportType
from apps.report.serializers import ReportSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker


class ReportCreateInputType(graphene.InputObjectType):
    name = graphene.String(required=True)
    analysis = graphene.String(required=False)
    methodology = graphene.String(required=False)
    significant_updates = graphene.String(required=False)
    challenges = graphene.String(required=False)
    summary = graphene.String(required=False)
    event_countries = graphene.List(graphene.NonNull(graphene.ID), required=False)
    event_crises = graphene.List(graphene.NonNull(graphene.ID), required=False)
    figure_start_after = graphene.Date(required=True)
    figure_end_before = graphene.Date(required=True)
    event_crisis_types = graphene.List(graphene.NonNull(CrisisTypeGrapheneEnum), required=False)


class ReportUpdateInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    name = graphene.String()
    analysis = graphene.String(required=False)
    methodology = graphene.String(required=False)
    significant_updates = graphene.String(required=False)
    challenges = graphene.String(required=False)
    summary = graphene.String(required=False)
    event_countries = graphene.List(graphene.NonNull(graphene.ID), required=False)
    event_crises = graphene.List(graphene.NonNull(graphene.ID), required=False)
    figure_start_after = graphene.Date(required=False)
    figure_end_before = graphene.Date(required=False)
    event_crisis_types = graphene.Date(required=False)


class CreateReport(graphene.Mutation):
    class Arguments:
        data = ReportCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ReportType)

    @staticmethod
    @permission_checker(['report.add_report'])
    def mutate(root, info, data):
        serializer = ReportSerializer(data=data)
        if errors := mutation_is_not_valid(serializer):
            return CreateReport(errors=errors, ok=False)
        instance = serializer.save()
        return CreateReport(result=instance, errors=None, ok=True)


class UpdateReport(graphene.Mutation):
    class Arguments:
        data = ReportUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ReportType)

    @staticmethod
    @permission_checker(['report.change_report'])
    def mutate(root, info, data):
        try:
            instance = Report.objects.get(id=data['id'])
        except Report.DoesNotExist:
            return UpdateReport(errors=[
                dict(field='nonFieldErrors', messages=gettext('Report does not exist.'))
            ])
        serializer = ReportSerializer(
            instance=instance, data=data, partial=True, context=dict(request=info.context)
        )
        if errors := mutation_is_not_valid(serializer):
            return UpdateReport(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateReport(result=instance, errors=None, ok=True)


class DeleteReport(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ReportType)

    @staticmethod
    @permission_checker(['report.delete_report'])
    def mutate(root, info, id):
        try:
            instance = Report.objects.get(id=id)
        except Report.DoesNotExist:
            return DeleteReport(errors=[
                dict(field='nonFieldErrors', messages=gettext('Report does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteReport(result=instance, errors=None, ok=True)


class Mutation(object):
    create_report = CreateReport.Field()
    update_report = UpdateReport.Field()
    delete_report = DeleteReport.Field()
