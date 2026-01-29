import django_filters

from apps.contact.models import Communication, CommunicationMedium, Contact
from apps.users.roles import USER_ROLE
from utils.filters import IDFilter, IDListFilter, MultiWordSearchFilterSet, StringListFilter, generate_type_for_filter_set


class ContactFilter(MultiWordSearchFilterSet):
    id = IDFilter(field_name="id", lookup_expr="exact")
    countries_of_operation = StringListFilter(method="filter_countries")

    class Meta:
        model = Contact
        fields = ["country"]
        search_fields = ["first_name", "last_name"]

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(countries_of_operation__in=value).distinct()

    @property
    def qs(self):
        if self.request.user.highest_role == USER_ROLE.GUEST.value:
            return super().qs.none()
        return super().qs.distinct()


class CommunicationFilter(MultiWordSearchFilterSet):
    id = IDFilter(field_name="id", lookup_expr="exact")

    class Meta:
        model = Communication
        fields = ["contact", "country"]
        search_fields = ["subject"]

    @property
    def qs(self):
        if self.request.user.highest_role == USER_ROLE.GUEST.value:
            return super().qs.none()
        return super().qs.distinct()


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
