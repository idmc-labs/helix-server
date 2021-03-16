from collections import OrderedDict

from django.utils.translation import gettext
from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.report.models import (
    Report,
    ReportComment,
    ReportGeneration,
    ReportApproval,
)
from utils.validations import is_child_parent_dates_valid


class ReportSerializer(MetaInformationSerializerMixin,
                       serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'

    def validate(self, attrs) -> dict:
        attrs = super().validate(attrs)
        errors = OrderedDict()
        errors.update(is_child_parent_dates_valid(
            attrs,
            self.instance,
            parent_field=None,
            c_start_field='filter_figure_start_after',
            c_end_field='filter_figure_end_before',
        ))
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class ReportCommentSerializer(MetaInformationSerializerMixin,
                              serializers.ModelSerializer):
    class Meta:
        model = ReportComment
        fields = '__all__'

    def validate_body(self, body):
        if not body.strip():
            raise serializers.ValidationError('Comment body is missing.')
        return body


class ReportSignoffSerializer(serializers.Serializer):
    report = serializers.IntegerField(required=True)

    def validate_report(self, report):
        if not ReportGeneration.objects.filter(
            report=report,
            is_signed_off=False
        ).exists():
            raise serializers.ValidationError(gettext('Nothing to sign off.'))
        return report

    def save(self):
        report_id = self.validated_data['report']
        report = Report.objects.get(id=report_id)
        report.sign_off(self.context['request'].user)
        return report


class ReportGenerationSerializer(MetaInformationSerializerMixin,
                                 serializers.ModelSerializer):
    class Meta:
        model = ReportGeneration
        fields = ['report']

    def validate_report(self, report):
        if report.generated_from != Report.REPORT_TYPE.GROUP:
            raise serializers.ValidationError(gettext('Cannot start generation for non-grid reports'))
        if ReportGeneration.objects.filter(
            report=report,
            is_signed_off=False
        ).exists():
            raise serializers.ValidationError(gettext('Cannot start another while previous is not signed off.'))
        return report


class ReportApproveSerializer(serializers.Serializer):
    report = serializers.IntegerField(required=True)
    is_approved = serializers.BooleanField(required=False)

    def validate_report(self, report):
        if not ReportGeneration.objects.filter(
            report_id=report,
            is_signed_off=False
        ).exists():
            raise serializers.ValidationError(gettext('Nothing to approve.'))
        return report

    def save(self):
        report = self.validated_data['report']
        generation = ReportGeneration.objects.get(
            report_id=report,
            is_signed_off=False,
        )
        ReportApproval.objects.update_or_create(
            generation=generation,
            created_by=self.context['request'].user,
            defaults=dict(
                is_approved=self.validated_data.get('is_approved', True),
            ),
        )
