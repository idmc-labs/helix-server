import django_filters
from django_filters import rest_framework as df

from utils.filters import IDListFilter, MultipleInputFilter

from .enums import HulkBulkImportStatusEnum
from .models import HulkBulkImport


class HulkBulkImportFilter(df.FilterSet):
    status_list = MultipleInputFilter(HulkBulkImportStatusEnum, field_name="status")
    created_by_ids = IDListFilter(method="filter_created_by")
    created_at_gte = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_at_lte = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = HulkBulkImport
        fields = []

    def filter_created_by(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(created_by__in=value)
