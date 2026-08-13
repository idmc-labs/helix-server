import django_filters
from django.db.models import Exists, Max, Min, OuterRef, Subquery

from apps.contact.models import Communication, CommunicationMedium, Contact
from apps.country.models import Country
from apps.users.roles import USER_ROLE
from utils.filters import (
    AcceptsOrdering,
    IDFilter,
    IDListFilter,
    MultiWordSearchFilterSet,
    StringListFilter,
    generate_type_for_filter_set,
)


class ContactFilter(AcceptsOrdering, MultiWordSearchFilterSet):
    id = IDFilter(field_name="id", lookup_expr="exact")
    countries_of_operation = StringListFilter(method="filter_countries")

    class Meta:
        model = Contact
        fields = ["country"]
        multi_word_search_fields = ["first_name", "last_name"]

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(
            Exists(Contact.countries_of_operation.through.objects.filter(contact_id=OuterRef("pk"), country_id__in=value))
        )

    @property
    def qs(self):
        if self.request.user.highest_role == USER_ROLE.GUEST.value:
            return super().qs.none()
        # No .distinct(): the only fan-out filter (countries_of_operation) now uses Exists
        # and multi-word search is Exists-based, so nothing multiplies rows.
        queryset = super().qs
        # ORDERING by the M2M does still fan out, though — denormalise it to a per-contact
        # scalar aliased to the ordering token. A correlated subquery rather than the
        # whole-table CTE the large lists use: sorting needs the key for every filtered row
        # before the LIMIT, and on a table this small the per-row aggregate beats aggregating
        # the whole table to serve one page. Built only when the list is sorted by it.
        # Min ascending / Max descending: that is the country the fan-out join sorted the
        # contact at (see EventFilter.qs for the full reasoning).
        if "countries_of_operation__idmc_short_name" in self.ordering_fields:
            aggregate = Max if "countries_of_operation__idmc_short_name" in self.descending_ordering_fields else Min
            queryset = queryset.annotate(
                **{
                    "countries_of_operation__idmc_short_name": Subquery(
                        Country.objects.filter(operating_contacts=OuterRef("pk"))
                        .order_by()
                        .values("operating_contacts")
                        .annotate(key=aggregate("idmc_short_name"))
                        .values("key")[:1]
                    )
                }
            )
        return queryset


class CommunicationFilter(MultiWordSearchFilterSet):
    id = IDFilter(field_name="id", lookup_expr="exact")

    class Meta:
        model = Communication
        fields = ["contact", "country"]
        multi_word_search_fields = ["subject"]

    @property
    def qs(self):
        if self.request.user.highest_role == USER_ROLE.GUEST.value:
            return super().qs.none()
        # No .distinct(): no filter on this set crosses a to-many relation.
        return super().qs


class CommunicationMediumFilter(django_filters.FilterSet):
    ids = IDListFilter(field_name="id")

    class Meta:
        model = CommunicationMedium
        fields = []


ContactFilterDataType, ContactFilterDataInputType = generate_type_for_filter_set(
    ContactFilter,
    "contact.schema.contact_list",
    "ContactFilterDataType",
    "ContactFilterDataInputType",
)
