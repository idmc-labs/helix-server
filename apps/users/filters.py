from django.contrib.auth.models import Permission
from django.db.models import Value
from django.db.models.functions import Lower, StrIndex, Concat, Coalesce
import django_filters

from apps.users.models import User
from utils.filters import AllowInitialFilterSetMixin, StringListFilter


class UserFilter(AllowInitialFilterSetMixin, django_filters.FilterSet):
    role = django_filters.CharFilter(field_name='groups__name',
                                     lookup_expr='iexact',
                                     distinct=True)
    roleIn = StringListFilter(method='filter_role_in')
    full_name = django_filters.CharFilter(method='filter_full_name')
    id = django_filters.CharFilter(field_name='id', lookup_expr='iexact')
    is_active = django_filters.CharFilter(method='filter_is_active')

    class Meta:
        model = User
        fields = ['email']

    def filter_is_active(self, queryset, name, value):
        value = value.lower()
        if value in ['true', 'false']:
            return queryset.filter(is_active=value == 'true')
        return queryset

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
            full=Coalesce(
                Lower('full_name'),
                Concat(Lower('first_name'), Value(' '), Lower('last_name')),
            )
        ).annotate(
            idx=StrIndex('full', Value(value.lower()))
        ).filter(idx__gt=0).order_by('idx')


class ReviewerUserFilter(UserFilter):
    @property
    def qs(self):
        return super().qs.filter(
            groups__permissions__id=Permission.objects.get(codename='add_review').id
        )
