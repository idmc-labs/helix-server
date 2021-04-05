import graphene
from django.utils.translation import gettext

from apps.report.models import (
    Report,
    ReportComment,
)
from apps.report.schema import ReportType, ReportCommentType
from apps.report.serializers import (
    ReportSerializer,
    ReportUpdateSerializer,
    ReportCommentSerializer,
    ReportGenerationSerializer,
    ReportApproveSerializer,
    ReportSignoffSerializer,
)
from utils.mutation import generate_input_type_for_serializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker


ReportCreateInputType = generate_input_type_for_serializer(
    'ReportCreateInputType',
    ReportSerializer
)

ReportUpdateInputType = generate_input_type_for_serializer(
    'ReportUpdateInputType',
    ReportUpdateSerializer
)


class CreateReport(graphene.Mutation):
    class Arguments:
        data = ReportCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ReportType)

    @staticmethod
    @permission_checker(['report.add_report'])
    def mutate(root, info, data):
        serializer = ReportSerializer(data=data, context=dict(request=info.context.request))
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
            instance=instance, data=data, partial=True, context=dict(request=info.context.request)
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


class ReportCommentCreateInputType(graphene.InputObjectType):
    body = graphene.String(required=True)
    report = graphene.ID(required=True)


class ReportCommentUpdateInputType(graphene.InputObjectType):
    body = graphene.String(required=True)
    id = graphene.ID(required=True)


class CreateReportComment(graphene.Mutation):
    class Arguments:
        data = ReportCommentCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ReportCommentType)

    @staticmethod
    @permission_checker(['report.add_reportcomment'])
    def mutate(root, info, data):
        serializer = ReportCommentSerializer(data=data, context=dict(request=info.context.request))
        if errors := mutation_is_not_valid(serializer):
            return CreateReportComment(errors=errors, ok=False)
        instance = serializer.save()
        return CreateReportComment(result=instance, errors=None, ok=True)


class UpdateReportComment(graphene.Mutation):
    class Arguments:
        data = ReportCommentUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ReportCommentType)

    @staticmethod
    @permission_checker(['report.change_reportcomment'])
    def mutate(root, info, data):
        try:
            instance = ReportComment.objects.get(id=data['id'],
                                                 created_by=info.context.user)
        except ReportComment.DoesNotExist:
            return UpdateReportComment(errors=[
                dict(field='nonFieldErrors', messages=gettext('Comment does not exist.'))
            ])
        serializer = ReportCommentSerializer(
            instance=instance, data=data, partial=True, context=dict(request=info.context.request)
        )
        if errors := mutation_is_not_valid(serializer):
            return UpdateReportComment(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateReportComment(result=instance, errors=None, ok=True)


class DeleteReportComment(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ReportCommentType)

    @staticmethod
    @permission_checker(['report.delete_reportcomment'])
    def mutate(root, info, id):
        try:
            instance = ReportComment.objects.get(id=id,
                                                 created_by=info.context.user)
        except ReportComment.DoesNotExist:
            return DeleteReportComment(errors=[
                dict(field='nonFieldErrors', messages=gettext('Comment does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteReportComment(result=instance, errors=None, ok=True)


class GenerateReport(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ReportType)

    @staticmethod
    @permission_checker(['report.sign_off_report'])
    def mutate(root, info, id):
        try:
            instance = Report.objects.get(id=id)
        except Report.DoesNotExist:
            return GenerateReport(errors=[
                dict(field='nonFieldErrors', messages=gettext('Report does not exist.'))
            ])
        serializer = ReportGenerationSerializer(
            data=dict(report=instance.id),
            context=dict(request=info.context.request),
        )
        if errors := mutation_is_not_valid(serializer):
            return GenerateReport(errors=errors, ok=False)
        serializer.save()
        return GenerateReport(result=instance, errors=None, ok=True)


class SignOffReport(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        include_history = graphene.Boolean(required=False)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ReportType)

    @staticmethod
    @permission_checker(['report.sign_off_report'])
    def mutate(root, info, id, include_history):
        try:
            instance = Report.objects.get(id=id)
        except Report.DoesNotExist:
            return SignOffReport(errors=[
                dict(field='nonFieldErrors', messages=gettext('Report does not exist.'))
            ])
        serializer = ReportSignoffSerializer(
            data=dict(
                report=id,
                include_history=include_history or False
            ),
            context=dict(request=info.context.request),
        )
        if errors := mutation_is_not_valid(serializer):
            return SignOffReport(errors=errors, ok=False)
        instance = serializer.save()
        instance.refresh_from_db()
        return SignOffReport(result=instance, errors=None, ok=True)


class ApproveReport(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        approve = graphene.Boolean(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ReportType)

    @staticmethod
    @permission_checker(['report.approve_report'])
    def mutate(root, info, id, approve):
        try:
            instance = Report.objects.get(id=id)
        except Report.DoesNotExist:
            return ApproveReport(errors=[
                dict(field='nonFieldErrors', messages=gettext('Report does not exist.'))
            ])
        serializer = ReportApproveSerializer(
            data=dict(
                report=id,
                is_approved=approve,
            ),
            context=dict(request=info.context.request),
        )
        if errors := mutation_is_not_valid(serializer):
            return ApproveReport(errors=errors, ok=False)
        serializer.save()
        return ApproveReport(result=instance, errors=None, ok=True)


class Mutation(object):
    create_report = CreateReport.Field()
    update_report = UpdateReport.Field()
    delete_report = DeleteReport.Field()
    # report comment
    create_report_comment = CreateReportComment.Field()
    update_report_comment = UpdateReportComment.Field()
    delete_report_comment = DeleteReportComment.Field()

    approve_report = ApproveReport.Field()
    start_report_generation = GenerateReport.Field()
    sign_off_report = SignOffReport.Field()
