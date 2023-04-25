from django.utils.translation import gettext
import graphene
from graphene_django.filter.utils import get_filtering_args_from_filterset

from apps.contrib.serializers import ExcelDownloadSerializer
from apps.report.models import (
    Report,
    ReportComment,
)
from apps.report.filters import ReportFilter
from apps.report.schema import ReportType, ReportCommentType
from apps.report.serializers import (
    ReportSerializer,
    ReportUpdateSerializer,
    ReportCommentSerializer,
    ReportGenerationSerializer,
    ReportApproveSerializer,
    ReportSignoffSerializer,
    check_is_pfa_visible_in_gidd,
)
from utils.mutation import generate_input_type_for_serializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker
from utils.common import convert_date_object_to_string_in_dict


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


class ExportReportFigures(graphene.Mutation):
    class Arguments:
        report = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, **kwargs):
        from apps.contrib.models import ExcelDownload

        serializer = ExcelDownloadSerializer(
            data=dict(
                download_type=int(ExcelDownload.DOWNLOAD_TYPES.FIGURE),
                filters=convert_date_object_to_string_in_dict(kwargs),
            ),
            context=dict(request=info.context.request)
        )
        if errors := mutation_is_not_valid(serializer):
            return ExportReportFigures(errors=errors, ok=False)
        serializer.save()
        return ExportReportFigures(errors=None, ok=True)


class ExportReports(graphene.Mutation):
    class Meta:
        arguments = get_filtering_args_from_filterset(
            ReportFilter,
            ReportType
        )

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, **kwargs):
        from apps.contrib.models import ExcelDownload

        serializer = ExcelDownloadSerializer(
            data=dict(
                download_type=int(ExcelDownload.DOWNLOAD_TYPES.REPORT),
                filters=convert_date_object_to_string_in_dict(kwargs),
            ),
            context=dict(request=info.context.request)
        )
        if errors := mutation_is_not_valid(serializer):
            return ExportReports(errors=errors, ok=False)
        serializer.save()
        return ExportReports(errors=None, ok=True)


class ExportReport(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ReportType)

    @staticmethod
    def mutate(root, info, id):
        from apps.contrib.models import ExcelDownload
        try:
            instance = Report.objects.get(id=id)
        except Report.DoesNotExist:
            return ExportReport(errors=[
                dict(field='nonFieldErrors', messages=gettext('Report does not exist.'))
            ])
        serializer = ExcelDownloadSerializer(
            data=dict(
                download_type=int(ExcelDownload.DOWNLOAD_TYPES.INDIVIDUAL_REPORT),
                filters=dict(),
                model_instance_id=instance.id
            ),
            context=dict(request=info.context.request)
        )
        if errors := mutation_is_not_valid(serializer):
            return ExportReport(errors=errors, ok=False)
        serializer.save()
        return ExportReport(errors=None, ok=True)


class SetPfaVisibleInGidd(graphene.Mutation):
    class Arguments:
        report_id = graphene.ID(required=True)
        is_pfa_visible_in_gidd = graphene.Boolean(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ReportType)

    @staticmethod
    @permission_checker(['report.update_pfa_visibility_report'])
    def mutate(root, info, report_id, is_pfa_visible_in_gidd):
        report = Report.objects.filter(id=report_id).first()
        if not report:
            return SetPfaVisibleInGidd(errors=[
                dict(field='nonFieldErrors', messages='Report does not exist')
            ])
        errors = check_is_pfa_visible_in_gidd(report)
        if errors:
            return SetPfaVisibleInGidd(errors=[
                dict(field='nonFieldErrors', messages=errors)
            ])
        if is_pfa_visible_in_gidd is True:
            errors = check_is_pfa_visible_in_gidd(report)
            if errors:
                return SetPfaVisibleInGidd(errors=[
                    dict(field='nonFieldErrors', messages=errors)
                ])
        report.is_pfa_visible_in_gidd = is_pfa_visible_in_gidd
        report.save()
        return SetPfaVisibleInGidd(result=report, errors=None, ok=True)


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
    # export
    export_report_figures = ExportReportFigures.Field()
    export_reports = ExportReports.Field()
    export_report = ExportReport.Field()
    set_pfa_visible_in_gidd = SetPfaVisibleInGidd.Field()
