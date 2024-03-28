from django.db.models import (
    Exists,
    Subquery,
    OuterRef,
    Q,
    F,
    When,
    Case,
    Value,
    BooleanField,
)
from django_filters import rest_framework as df

from apps.report.models import Report, ReportGeneration, ReportApproval, ReportComment
from utils.filters import IDListFilter, StringListFilter, generate_type_for_filter_set


class ReportFilter(df.FilterSet):
    filter_figure_countries = IDListFilter(method='filter_countries')
    review_status = StringListFilter(method='filter_by_review_status')
    start_date_after = df.DateFilter(method='filter_date_after')
    end_date_before = df.DateFilter(method='filter_end_date_before')
    is_public = df.BooleanFilter(method='filter_is_public')
    is_gidd_report = df.BooleanFilter(method='filter_is_gidd_report')
    is_pfa_visible_in_gidd = df.BooleanFilter(method='filter_is_pfa_visible_in_gidd')

    class Meta:
        model = Report
        fields = {
            'name': ['unaccent__icontains'],
            'change_in_source': ['exact'],
            'change_in_methodology': ['exact'],
            'change_in_data_availability': ['exact'],
            'retroactive_change': ['exact']
        }

    def filter_countries(self, qs, name, value):
        if value:
            return qs.filter(filter_figure_countries__in=value).distinct()
        return qs

    def filter_by_review_status(self, qs, name, value):
        if not value:
            return qs
        qs = qs.annotate(
            _last_generation_id=Subquery(
                ReportGeneration.objects.filter(
                    report=OuterRef('pk')
                ).order_by('-created_by').values('pk')[:1]
            )
        ).annotate(
            # is_signed_off already exists
            _is_signed_off=F('is_signed_off'),
            _is_approved=Exists(
                ReportApproval.objects.filter(
                    generation=OuterRef('_last_generation_id'),
                    is_approved=True,
                )
            ),
        ).annotate(
            _is_unapproved=Case(
                When(
                    Q(_is_approved=False) & Q(_is_signed_off=False),
                    then=Value(True)
                ),
                default=Value(False),
                output_field=BooleanField()
            )
        )
        _temp = qs.none()
        if Report.REPORT_REVIEW_FILTER.SIGNED_OFF.name in value:
            signed_off = qs.filter(_is_signed_off=True)
            _temp = _temp | signed_off
        if Report.REPORT_REVIEW_FILTER.APPROVED.name in value:
            approved = qs.filter(_is_approved=True)
            _temp = _temp | approved
        if Report.REPORT_REVIEW_FILTER.UNAPPROVED.name in value:
            unapproved = qs.filter(_is_unapproved=True)
            _temp = _temp | unapproved
        return _temp

    def filter_date_after(self, qs, name, value):
        if value:
            return qs.filter(filter_figure_start_after__gte=value)
        return qs

    def filter_end_date_before(self, qs, name, value):
        if value:
            return qs.filter(filter_figure_end_before__lte=value)
        return qs

    def filter_is_public(self, qs, name, value):
        if value is True:
            return qs.filter(is_public=True)
        if value is False:
            user = self.request.user
            return qs.filter(is_public=False, created_by=user)
        return qs

    def filter_is_gidd_report(self, qs, name, value):
        if value is True:
            return qs.filter(is_gidd_report=True)
        if value is False:
            return qs.filter(is_gidd_report=False)
        return qs

    def filter_is_pfa_visible_in_gidd(self, qs, name, value):
        if value is True:
            return qs.filter(is_pfa_visible_in_gidd=True)
        if value is False:
            return qs.filter(is_pfa_visible_in_gidd=False)
        return qs

    @property
    def qs(self):
        # Return private reports by default if filter is not applied
        is_public = self.data.get('is_public')
        if is_public is None:
            user = self.request.user
            return super().qs.filter(
                Q(is_public=True) | Q(is_public=False, created_by=user)
            )

        return super().qs.distinct()


class DummyFilter(df.FilterSet):
    """
    NOTE: Created to override the default filters of list types
    """
    id = df.CharFilter(field_name='id', lookup_expr='exact')


class ReportApprovalFilter(df.FilterSet):
    class Meta:
        model = ReportApproval
        fields = ('is_approved',)


class ReportGenerationFilter(df.FilterSet):
    class Meta:
        model = ReportGeneration
        fields = ('report',)


class ReportCommentFilter(df.FilterSet):
    ids = IDListFilter(field_name='id')

    class Meta:
        model = ReportComment
        fields = []


ReportFilterDataType, ReportFilterDataInputType = generate_type_for_filter_set(
    ReportFilter,
    'report.schema.report_list',
    'ReportFilterDataType',
    'ReportFilterDataInputType',
)
