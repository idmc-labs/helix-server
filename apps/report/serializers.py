from collections import OrderedDict

from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.report.models import (
    Report,
    ReportComment,
)
from utils.validations import is_child_parent_dates_valid


class ReportSerializer(MetaInformationSerializerMixin,
                       serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'

    def validate(self, attrs) -> dict:
        errors = OrderedDict()
        errors.update(is_child_parent_dates_valid(
            attrs,
            self.instance,
            parent_field=None,
            c_start_field='figure_start_after',
            c_end_field='figure_end_before',
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
