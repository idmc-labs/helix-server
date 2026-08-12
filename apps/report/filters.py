from django.db.models import (
    BooleanField,
    Case,
    Exists,
    F,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django_filters import rest_framework as df

from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.report.models import Report, ReportApproval, ReportComment, ReportGeneration
from utils.filters import IDListFilter, MultiWordSearchFilterSet, StringListFilter, generate_type_for_filter_set


class ReportFilter(MultiWordSearchFilterSet):
    filter_figure_countries = IDListFilter(method="filter_countries")
    review_status = StringListFilter(method="filter_by_review_status")
    start_date_after = df.DateFilter(method="filter_date_after")
    end_date_before = df.DateFilter(method="filter_end_date_before")
    is_public = df.BooleanFilter(method="filter_is_public")
    is_gidd_report = df.BooleanFilter(method="filter_is_gidd_report")
    is_pfa_visible_in_gidd = df.BooleanFilter(method="filter_is_pfa_visible_in_gidd")
    filter_figure_crisis_types = StringListFilter(method="filter_by_filter_figure_crisistype")
    filter_figure_categories = StringListFilter(method="filter_by_filter_figure_categories")

    class Meta:
        model = Report
        fields = {
            "change_in_source": ["exact"],
            "change_in_methodology": ["exact"],
            "change_in_data_availability": ["exact"],
            "retroactive_change": ["exact"],
        }
        multi_word_search_fields = ["name"]

    def filter_by_filter_figure_crisistype(self, qs, name, value):
        enum_values = [Crisis.CRISIS_TYPE[crisis_type].value for crisis_type in value]
        return qs.filter(filter_figure_crisis_types__overlap=enum_values)

    def filter_by_filter_figure_categories(self, qs, name, value):
        enum_values = [Figure.FIGURE_CATEGORY_TYPES[category].value for category in value]
        return qs.filter(filter_figure_categories__overlap=enum_values)

    def filter_countries(self, qs, name, value):
        if value:
            # M2M: Exists membership, no fan-out -> no .distinct().
            return qs.filter(
                Exists(Report.filter_figure_countries.through.objects.filter(report_id=OuterRef("pk"), country_id__in=value))
            )
        return qs

    def filter_by_review_status(self, qs, name, value):
        if not value:
            return qs
        qs = (
            qs.annotate(
                # The same "last" as Report.last_generation and ReportLastGenerationLoader:
                # newest by creation time, pk breaking a tie. Ordering by created_by picked the
                # generation belonging to the highest user id instead, so a report's review status
                # was read off a generation the client is never shown.
                _last_generation_id=Subquery(
                    ReportGeneration.objects.filter(report=OuterRef("pk")).order_by("-created_at", "-id").values("pk")[:1]
                )
            )
            .annotate(
                # is_signed_off already exists
                _is_signed_off=F("is_signed_off"),
                _is_approved=Exists(
                    ReportApproval.objects.filter(
                        generation=OuterRef("_last_generation_id"),
                        is_approved=True,
                    )
                ),
            )
            .annotate(
                _is_unapproved=Case(
                    When(Q(_is_approved=False) & Q(_is_signed_off=False), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                )
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
        is_public = self.data.get("is_public")
        if is_public is None:
            user = self.request.user
            return super().qs.filter(Q(is_public=True) | Q(is_public=False, created_by=user))

        # No global .distinct(): the only filter that fans out (filter_countries, an
        # M2M join) applies its own .distinct(), and the multi-word search uses Exists
        # (no join fan-out). A blanket DISTINCT here forces a Unique over every column
        # on top of the created_at index scan for nothing. Id-set verified identical.
        return super().qs


class DummyFilter(df.FilterSet):
    """
    NOTE: Created to override the default filters of list types
    """

    id = df.CharFilter(field_name="id", lookup_expr="exact")


class ReportApprovalFilter(df.FilterSet):
    class Meta:
        model = ReportApproval
        fields = ("is_approved",)


class ReportGenerationFilter(df.FilterSet):
    class Meta:
        model = ReportGeneration
        fields = ("report",)


class ReportCommentFilter(df.FilterSet):
    ids = IDListFilter(field_name="id")

    class Meta:
        model = ReportComment
        fields = []


ReportFilterDataType, ReportFilterDataInputType = generate_type_for_filter_set(
    ReportFilter,
    "report.schema.report_list",
    "ReportFilterDataType",
    "ReportFilterDataInputType",
)
