import django_filters

from apps.contact.models import Contact
from django.contrib.auth.models import Group


class UserFilter(django_filters.FilterSet):
    role = django_filters.CharFilter(method='filter_role')
    roleIn = django_filters.CharFilter(method='filter_role_in')

    class Meta:
        model = Contact
        fields = ['email']

    def filter_role(self, queryset, name, value):
        if not value:
            return queryset
        group = Group.objects.get(name__iexact=value)
        return queryset.filter(
            groups=group
        ).distinct()

    def filter_role_in(self, queryset, name, value):
        if not value:
            return queryset
        groups = []
        for v in value.strip(',').replace(' ', '').split(','):
            groups.append(Group.objects.get(name__iexact=v))
        return queryset.filter(
            groups__in=groups
        ).distinct()
