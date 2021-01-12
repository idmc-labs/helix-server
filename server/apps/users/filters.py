from django.db.models import Value
from django.db.models.functions import Lower, StrIndex, Concat
import django_filters

from apps.users.models import User
from utils.filters import StringListFilter


class UserFilter(django_filters.FilterSet):
    role = django_filters.CharFilter(field_name='groups__name',
                                     lookup_expr='iexact',
                                     distinct=True)
    roleIn = StringListFilter(method='filter_role_in')
    full_name = django_filters.CharFilter(method='filter_full_name')
    include_inactive = django_filters.BooleanFilter(method='filter_noop')
    id = django_filters.CharFilter(field_name='id', lookup_expr='iexact')

    class Meta:
        model = User
        fields = ['email']

    def filter_role_in(self, queryset, name, value):
        if not value:
            return queryset
        # NOTE: role names (permission group names) are always upper cased
        # server/apps/users/roles.py:6
        value = [each.upper() for each in value]
        return queryset.filter(
            groups__name__in=value
        ).distinct()

    def filter_full_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.annotate(
            full=Concat(Lower('first_name'), Lower('last_name'))
        ).annotate(
            idx=StrIndex('full', Value(value.lower()))
        ).filter(idx__gt=0).order_by('idx', 'full')

    def filter_noop(self, queryset, name, value):
        return queryset

    @property
    def qs(self):
        include_inactive = self.data.get('include_inactive', False)
        if not include_inactive:
            return super().qs.filter(is_active=True)
        return super().qs
