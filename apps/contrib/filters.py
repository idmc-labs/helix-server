import django_filters

from apps.contrib.models import ExcelDownload


class ExcelExportFilter(django_filters.FilterSet):
    class Meta:
        model = ExcelDownload
        fields = {
            'started_at': ['lt', 'gt', 'gte', 'lte']
        }

    @property
    def qs(self):
        return super().qs.filter(
            created_by=self.request.user
        )
