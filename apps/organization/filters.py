import django_filters
from django.db.models import Case, Exists, Max, Min, OuterRef, Subquery, When

from apps.country.models import Country
from apps.organization.models import Organization, OrganizationKind
from utils.filters import (
    IDListFilter,
    MultiWordSearchFilterSet,
    StringListFilter,
    generate_type_for_filter_set,
)
from utils.graphene.ordering import strip_direction


class OrganizationFilter(MultiWordSearchFilterSet):
    # The client's organization table exposes `countries__idmc_short_name` as a sortable
    # column, and ordering by that M2M path JOIN-fans-out one organization into one row per
    # country. Take the active ordering so the sort key can be denormalised into a
    # per-organization scalar (see `qs` below).
    accepts_ordering = True

    countries = IDListFilter(method="filter_countries")
    categories = StringListFilter(method="filter_categories")
    organization_kinds = IDListFilter(method="filter_organization_kinds")
    order_country_first = IDListFilter(method="filter_order_country_first")
    exclude_deleted = django_filters.BooleanFilter(method="filter_exclude_deleted")

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

    def filter_exclude_deleted(self, qs, name, value):
        # Archived organizations are shown unless a caller asks otherwise, and the asking
        # happens HERE rather than through a default: a filtering default manager, or a
        # filterset that hides on its own initiative, also removes the row from
        # entry.publishers / figure.sources, which drops attribution from live records that
        # were never archived (see SoftDeleteModel). The lists that offer organizations for
        # selection pass `excludeDeleted: true`.
        if value:
            return qs.filter(deleted_on__isnull=True)
        return qs

    def filter_order_country_first(self, qs, name, value):
        if not value:
            return qs
        country_organization_ids = qs.filter(
            Exists(Organization.countries.through.objects.filter(organization_id=OuterRef("pk"), country_id__in=value))
        ).values("id")
        return qs.order_by(Case(When(id__in=country_organization_ids, then=0), default=1))

    def __init__(self, *args, ordering=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ordering_fields = {strip_direction(field) for field in ordering.split(",") if field} if ordering else set()
        # A denormalised to-many sort key depends on the direction it is sorted in, which
        # `ordering_fields` has stripped off.
        self.descending_ordering_fields = (
            {strip_direction(field) for field in ordering.split(",") if field.startswith("-")} if ordering else set()
        )

    @property
    def qs(self):
        queryset = super().qs
        # Denormalise the M2M sort key into a per-organization scalar so the list stays one
        # row per organization. A correlated subquery rather than the whole-table CTE the
        # large lists use: sorting needs the key for every filtered row before the LIMIT, and
        # on a table this small the per-row aggregate beats aggregating the whole table to
        # serve one page. The annotation is aliased to the ordering token so order_by binds
        # to it instead of re-traversing the M2M. Only built when the list is sorted by it.
        # Min ascending / Max descending: that is the country the fan-out join sorted the
        # organization at (see EventFilter.qs for the full reasoning).
        if "countries__idmc_short_name" in self.ordering_fields:
            aggregate = Max if "countries__idmc_short_name" in self.descending_ordering_fields else Min
            sort_key = (
                Country.objects.filter(organizations=OuterRef("pk"))
                .order_by()
                .values("organizations")
                .annotate(key=aggregate("idmc_short_name"))
                .values("key")[:1]
            )
            queryset = queryset.annotate(**{"countries__idmc_short_name": Subquery(sort_key)})
        return queryset


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
