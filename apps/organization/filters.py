import django_filters
from apps.organization.models import Organization
from utils.filters import NameFilterMixin, IDListFilter, StringListFilter


class OrganizationFilter(NameFilterMixin,
                         django_filters.FilterSet):
    countries = IDListFilter(method='filter_countries')
    categories = StringListFilter(method='filter_categories')
    organization_kinds = IDListFilter(method='filter_organization_kinds')

    class Meta:
        model = Organization
        fields = {
            'name': ['unaccent__icontains'],
            'short_name': ['unaccent__icontains'],
        }

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(countries__in=value).distinct()

    def filter_categories(self, qs, name, value):
        if not value:
            return qs
        categories = [Organization.ORGANIZATION_CATEGORY.get(item).value for item in value]
        return qs.filter(category__in=categories)

    def filter_organization_kinds(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(organization_kind__in=value).distinct()

    @property
    def qs(self):
        return super().qs.select_related('organization_kind').prefetch_related("countries")
