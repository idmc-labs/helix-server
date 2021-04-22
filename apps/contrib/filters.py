import django_filters

from apps.contrib.models import ExcelDownload
from utils.filters import StringListFilter


class ExcelExportFilter(django_filters.FilterSet):
    status_list = StringListFilter(method='filter_status')

    class Meta:
        model = ExcelDownload
        fields = {
            'started_at': ['lt', 'gt', 'gte', 'lte']
        }

    def filter_status(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # internal filtering
                return qs.filter(status__in=value).distinct()
            # client side filtering
            return qs.filter(crisis_type__in=[
                ExcelDownload.EXCEL_GENERATION_STATUS.get(item).value for item in value
            ]).distinct()
        return qs

    @property
    def qs(self):
        return super().qs.filter(
            created_by=self.request.user
        )
