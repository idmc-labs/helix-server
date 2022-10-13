from django.db.models import Q
from django_filters import rest_framework as df
from apps.report.models import Report
from utils.filters import IDListFilter


class ReportFilter(df.FilterSet):
    filter_figure_countries = IDListFilter(method='filter_countries')
    start_date_after = df.DateFilter(method='filter_date_after')
    end_date_before = df.DateFilter(method='filter_end_date_before')
    is_public = df.BooleanFilter(method='filter_is_public', initial=False)

    class Meta:
        model = Report
        fields = {
            'name': ['unaccent__icontains'],
        }

    def filter_countries(self, qs, name, value):
        if value:
            return qs.filter(filter_figure_countries__in=value).distinct()
        return qs

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
