from django.db.models import Q
import django_filters

from apps.users.roles import USER_ROLE
from apps.contact.models import Contact, Communication
from utils.filters import StringListFilter


class ContactFilter(django_filters.FilterSet):
    id = django_filters.CharFilter(field_name='id', lookup_expr='iexact')
    first_name_contains = django_filters.CharFilter(field_name='first_name', lookup_expr='unaccent__icontains')
    last_name_contains = django_filters.CharFilter(field_name='last_name', lookup_expr='unaccent__icontains')
    name_contains = django_filters.CharFilter(method='filter_name_contains')
    countries_of_operation = StringListFilter(method='filter_countries')

    class Meta:
        model = Contact
        fields = ['country']

    def filter_name_contains(self, qs, name, value):
        return qs.filter(Q(first_name__unaccent__icontains=value) | Q(last_name__unaccent__icontains=value))

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(countries_of_operation__in=value).distinct()

    @property
    def qs(self):
        if self.request.user.highest_role == USER_ROLE.GUEST.value:
            return super().qs.none()
        return super().qs.distinct()


class CommunicationFilter(django_filters.FilterSet):
    id = django_filters.CharFilter(field_name='id', lookup_expr='iexact')
    subject_contains = django_filters.CharFilter(field_name='subject', lookup_expr='unaccent__icontains')

    class Meta:
        model = Communication
        fields = ['contact', 'country']

    @property
    def qs(self):
        if self.request.user.highest_role == USER_ROLE.GUEST.value:
            return super().qs.none()
        return super().qs.distinct()
