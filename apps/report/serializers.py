from rest_framework import serializers

from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.report.models import Report


class ReportSerializer(MetaInformationSerializerMixin,
                       serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'
