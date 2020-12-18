from django.db import models
import django_filters

from apps.contact.models import Contact, Communication


class ContactFilter(django_filters.FilterSet):
    id = django_filters.CharFilter(field_name='id', lookup_expr='iexact')
    first_name_contains = django_filters.CharFilter(field_name='first_name', lookup_expr='icontains')
    last_name_contains = django_filters.CharFilter(field_name='last_name', lookup_expr='icontains')
    name_contains = django_filters.CharFilter(method='filter_name_contains')

    class Meta:
        model = Contact
        fields = ['country']

    def filter_name_contains(self, qs, name, value):
        return qs.filter(models.Q(first_name__icontains=value) | models.Q(last_name__icontains=value))


class CommunicationFilter(django_filters.FilterSet):
    id = django_filters.CharFilter(field_name='id', lookup_expr='iexact')
    subject_contains = django_filters.CharFilter(field_name='subject', lookup_expr='icontains')

    class Meta:
        model = Communication
        fields = ['contact']
