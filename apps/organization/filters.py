import django_filters
from apps.organization.models import Organization
from utils.filters import NameFilterMixin, IDListFilter


class OrganizationFilter(NameFilterMixin,
                         django_filters.FilterSet):
    name = django_filters.CharFilter(method='_filter_name')
    countries = IDListFilter(method='filter_countries')
    categories = IDListFilter(method='filter_categories')
    organization_types = IDListFilter(method='filter_organization_types')

    class Meta:
        model = Organization
        fields = {
            'short_name': ['unaccent__icontains'],
        }

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(countries__in=value).distinct()

    def filter_categories(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(category__in=value).distinct()

    def filter_organization_types(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(organization_kind__in=value).distinct()

    @property
    def qs(self):
        return super().qs.select_related('countries', 'category', 'organization_kind')
