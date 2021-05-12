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

from apps.report.models import Report, ReportGeneration, ReportApproval
from utils.filters import IDListFilter, StringListFilter


class ReportFilter(df.FilterSet):
    filter_figure_countries = IDListFilter(method='filter_countries')
    review_status = StringListFilter(method='filter_by_review_status')

    class Meta:
        model = Report
        fields = {
            'name': ['icontains'],
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

    @property
    def qs(self):
        return super().qs.distinct()


class CountryReportFilter(df.FilterSet):
    """
    NOTE: following fields are predefined and annotated into the queryset
    """
    country = df.CharFilter(field_name='id', lookup_expr='exact')
