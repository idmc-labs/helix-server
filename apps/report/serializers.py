from collections import OrderedDict
import datetime

from django.utils.translation import gettext
from django.conf import settings
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.contrib.serializers import (
    MetaInformationSerializerMixin,
    UpdateSerializerMixin,
    IntegerIDField,
)
from apps.report.models import (
    Report,
    ReportComment,
    ReportGeneration,
    ReportApproval,
)
from apps.entry.models import Figure
from apps.crisis.models import Crisis
from apps.extraction.models import QueryAbstractModel
from apps.users.enums import USER_ROLE

from django.contrib.postgres.fields.array import ArrayField
from django.db.models.fields.related import ManyToManyField
from django.db.models.fields import BooleanField, CharField, DateField, TextField


def check_is_pfa_visible_in_gidd(report):
    errors = []
    if not report:
        errors.append('Report does not exist.')

    if not (report.filter_figure_start_after and report.filter_figure_end_before):
        errors.append('Start date and end date are required.')
    else:
        start_date_year = report.filter_figure_start_after.year
        start_date_month = report.filter_figure_start_after.month
        start_date_day = report.filter_figure_start_after.day

        end_date_year = report.filter_figure_end_before.year
        end_date_month = report.filter_figure_end_before.month
        end_date_day = report.filter_figure_end_before.day

        if not (
                start_date_year == end_date_year and
                start_date_month == 1 and
                start_date_day == 1 and
                end_date_month == 12 and
                end_date_day == 31
        ):
            errors.append('The report should span for the full year.')

    if not report.is_public:
        errors.append('Report should be public.')

    if report.filter_figure_countries.count() != 1:
        errors.append('Report should have exactly one country.')

    if not report.filter_figure_crisis_types:
        errors.append('Report should have conflict or disaster crisis type.')
    elif len(set(report.filter_figure_crisis_types).intersection({
        Crisis.CRISIS_TYPE.DISASTER,
        Crisis.CRISIS_TYPE.CONFLICT}
    )) != 1:
        errors.append('Report should have conflict or disaster crisis type.')

    if not report.filter_figure_categories:
        errors.append('Report should have IDPs or Internal Displacements category.')
    elif len(set(report.filter_figure_categories).intersection({
        Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
        Figure.FIGURE_CATEGORY_TYPES.IDPS,
    })) != 1:
        errors.append('Report should have IDPs or Internal Displacements category.')
    return errors


class ReportSerializer(MetaInformationSerializerMixin,
                       serializers.ModelSerializer):

    gidd_report_year = serializers.IntegerField(
        allow_null=True,
        required=False,
        validators=[
            UniqueValidator(
                queryset=Report.objects.all(),
                message=('GIDD report with this year already exists.'),
            ),
        ],
    )

    class Meta:
        model = Report
        fields = [
            'id', 'name', 'generated_from', 'analysis', 'methodology',
            'significant_updates', 'challenges', 'summary',
            'filter_figure_regions', 'filter_figure_countries',
            'filter_figure_crises', 'filter_figure_categories',
            'filter_figure_start_after', 'filter_figure_end_before',
            'filter_figure_crisis_types', 'filter_figure_geographical_groups',
            'filter_figure_events', 'filter_figure_tags', 'filter_figure_disaster_categories',
            'filter_figure_disaster_sub_categories', 'filter_figure_disaster_types',
            'filter_figure_disaster_sub_types', 'filter_figure_violence_types', 'filter_figure_violence_sub_types',
            'is_public', 'filter_figure_roles', 'public_figure_analysis', 'is_gidd_report', 'gidd_report_year',
            'change_in_source', 'change_in_methodology', 'change_in_data_availability', 'retroactive_change'
        ]

    def validate_dates(self, attrs):
        errors = OrderedDict()
        start = attrs.get('filter_figure_start_after', getattr(self.instance, 'filter_figure_start_after', None)),
        end = attrs.get('filter_figure_end_before', getattr(self.instance, 'filter_figure_end_before', None)),
        if start and end and start > end:
            errors.update(dict(
                filter_figure_start_after=gettext('Choose start date earlier than end date.')
            ))
        return errors

    def validate_gidd_report(self, attrs, errors):
        is_gidd_report = attrs.get('is_gidd_report', self.instance and self.instance.is_gidd_report)
        if is_gidd_report is True:
            year = attrs.get('gidd_report_year', self.instance and self.instance.gidd_report_year)

            if not year:
                raise serializers.ValidationError('For GIDD report year is required.')

            # Clear all query abstraction filter fields
            for field in QueryAbstractModel._meta.get_fields():
                # Reset values
                if isinstance(field, ArrayField):
                    attrs[field.name] = []
                elif isinstance(field, ManyToManyField):
                    attrs[field.name] = []
                elif type(field) in [BooleanField, CharField, DateField, TextField]:
                    attrs[field.name] = None
                else:
                    raise serializers.ValidationError('Unable to set filters for GIDD.')

            # Set these attrs when create or update
            attrs['filter_figure_start_after'] = datetime.datetime(year=year, month=1, day=1)
            attrs['filter_figure_end_before'] = datetime.datetime(year=year, month=12, day=31)
            attrs['is_public'] = True
            attrs['is_pfa_visible_in_gidd'] = False
        else:
            attrs['gidd_report_year'] = None

    @staticmethod
    def has_permission_for_report(user, report):
        roles = list(user.portfolios.values_list('role', flat=True))
        if USER_ROLE.ADMIN in roles:
            return True
        if USER_ROLE.REGIONAL_COORDINATOR in roles:
            return True
        if USER_ROLE.MONITORING_EXPERT in roles:
            return True
        if USER_ROLE.DIRECTORS_OFFICE in roles:
            return True
        if USER_ROLE.REPORTING_TEAM in roles:
            return report.created_by == user
        return False

    def validate(self, attrs) -> dict:
        if (
            self.instance is not None and
            not self.has_permission_for_report(
                self.context['request'].user,
                self.instance,
            )
        ):
            raise serializers.ValidationError('You do not have permission to edit report.')

        attrs = super().validate(attrs)
        errors = OrderedDict()
        errors.update(self.validate_dates(attrs))
        self.validate_gidd_report(attrs, errors)
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def update(self, instance, validated_data):
        validated_data['last_modified_by'] = self.context['request'].user
        instance = super().update(instance, validated_data)
        if check_is_pfa_visible_in_gidd(instance):
            instance.is_pfa_visible_in_gidd = False
            instance.save()
        return instance


class ReportUpdateSerializer(UpdateSerializerMixin, ReportSerializer):
    id = IntegerIDField(required=True)


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
    include_history = serializers.BooleanField(required=False)

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
        report.sign_off(
            self.context['request'].user,
            include_history=self.validated_data.get('include_history', False)
        )
        return report


class ReportGenerationSerializer(MetaInformationSerializerMixin,
                                 serializers.ModelSerializer):
    class Meta:
        model = ReportGeneration
        fields = ['report']

    def validate_report(self, report):
        if ReportGeneration.objects.filter(
            report=report
        ).count() == settings.GRAPHENE_DJANGO_EXTRAS['MAX_PAGE_SIZE']:
            raise serializers.ValidationError(
                gettext(
                    'Report Generation is limited to %(size)s only.'
                ) % {'size': settings.GRAPHENE_DJANGO_EXTRAS['MAX_PAGE_SIZE']}
            )
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

        # only one unsigned report can exist, this limit is ensured in ReportGenerationSerializer
        # during generation start...
        if ReportGeneration.objects.get(
            report=report,
            is_signed_off=False,
        ).approvers.count() == settings.GRAPHENE_DJANGO_EXTRAS['MAX_PAGE_SIZE']:
            raise serializers.ValidationError(
                gettext(
                    'Report approvals is limited to %(size)s only.'
                ) % {'size': settings.GRAPHENE_DJANGO_EXTRAS['MAX_PAGE_SIZE']}
            )
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
