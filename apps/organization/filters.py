import django_filters
from django.db.models import Case, When
from apps.organization.models import Organization, OrganizationKind
from utils.filters import (
    NameFilterMixin,
    IDListFilter,
    StringListFilter,
    generate_type_for_filter_set,
)


class OrganizationFilter(NameFilterMixin,
                         django_filters.FilterSet):
    countries = IDListFilter(method='filter_countries')
    categories = StringListFilter(method='filter_categories')
    organization_kinds = IDListFilter(method='filter_organization_kinds')
    order_country_first = IDListFilter(method='filter_order_country_first')

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

    def filter_order_country_first(self, qs, name, value):
        if not value:
            return qs
        country_organization_ids = qs.filter(countries__in=value).values('id').distinct()
        return qs.order_by(
            Case(
                When(id__in=country_organization_ids, then=0), default=1
            )
        )

    @property
    def qs(self):
        return super().qs.select_related('organization_kind').prefetch_related("countries")


class OrganizationKindFilter(django_filters.FilterSet):
    ids = IDListFilter(field_name='id')

    class Meta:
        model = OrganizationKind
        fields = []


OrganizationFilterDataType, OrganizationFilterDataInputType = generate_type_for_filter_set(
    OrganizationFilter,
    'organization.schema.organization_list',
    'OrganizationFilterDataType',
    'OrganizationFilterDataInputType',
)
