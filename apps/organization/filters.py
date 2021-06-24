import django_filters

from apps.organization.models import Organization
from utils.filters import NameFilterMixin


class OrganizationFilter(NameFilterMixin,
                         django_filters.FilterSet):
    name = django_filters.CharFilter(method='_filter_name')

    class Meta:
        model = Organization
        fields = []
