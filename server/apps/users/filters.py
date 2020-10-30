from django.contrib.auth.models import Group
import django_filters
import graphene

from apps.users.models import User
from utils.filters import _generate_list_filter_class


StringListFilter = _generate_list_filter_class(graphene.String)


class UserFilter(django_filters.FilterSet):
    role = django_filters.CharFilter(field_name='groups__name',
                                     lookup_expr='iexact',
                                     distinct=True)
    roleIn = StringListFilter(method='filter_role_in')

    class Meta:
        model = User
        fields = ['email']

    def filter_role_in(self, queryset, name, value):
        if not value:
            return queryset
        value = [each.upper() for each in value]
        return queryset.filter(
            groups__name__in=value
        ).distinct()
