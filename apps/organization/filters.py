import django_filters
from django.db.models import Case, Exists, OuterRef, When

from apps.organization.models import Organization, OrganizationKind
from utils.filters import (
    IDListFilter,
    MultiWordSearchFilterSet,
    StringListFilter,
    generate_type_for_filter_set,
)


class OrganizationFilter(MultiWordSearchFilterSet):
    countries = IDListFilter(method="filter_countries")
    categories = StringListFilter(method="filter_categories")
    organization_kinds = IDListFilter(method="filter_organization_kinds")
    order_country_first = IDListFilter(method="filter_order_country_first")

    class Meta:
        model = Organization
        fields = []
        multi_word_search_fields = ["name", "short_name", "countries__name"]

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(
            Exists(Organization.countries.through.objects.filter(organization_id=OuterRef("pk"), country_id__in=value))
        )

    def filter_categories(self, qs, name, value):
        if not value:
            return qs
        categories = [Organization.ORGANIZATION_CATEGORY.get(item).value for item in value]
        return qs.filter(category__in=categories)

    def filter_organization_kinds(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(organization_kind__in=value)

    def filter_order_country_first(self, qs, name, value):
        if not value:
            return qs
        country_organization_ids = qs.filter(
            Exists(Organization.countries.through.objects.filter(organization_id=OuterRef("pk"), country_id__in=value))
        ).values("id")
        return qs.order_by(Case(When(id__in=country_organization_ids, then=0), default=1))


class OrganizationKindFilter(django_filters.FilterSet):
    ids = IDListFilter(field_name="id")

    class Meta:
        model = OrganizationKind
        fields = []


OrganizationFilterDataType, OrganizationFilterDataInputType = generate_type_for_filter_set(
    OrganizationFilter,
    "organization.schema.organization_list",
    "OrganizationFilterDataType",
    "OrganizationFilterDataInputType",
)
