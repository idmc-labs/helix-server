from django.contrib.auth.models import Permission
from django.db import models
from django.db.models.functions import Lower, StrIndex, Concat, Coalesce
import django_filters
from django.db.models import Min

from apps.users.models import User, Portfolio
from apps.users.enums import USER_ROLE
from utils.filters import StringListFilter, IDListFilter


class UserFilter(django_filters.FilterSet):
    role_in = StringListFilter(method='filter_role_in')
    role_not_in = StringListFilter(method='filter_role_not_in')
    monitoring_sub_region_in = IDListFilter(method='filter_monitoring_sub_region_in')
    monitoring_sub_region_not_in = IDListFilter(method='filter_monitoring_sub_region_not_in')
    full_name = django_filters.CharFilter(method='filter_full_name')
    include_inactive = django_filters.BooleanFilter(method='filter_include_inactive')
    id = django_filters.CharFilter(field_name='id', lookup_expr='iexact')
    permissions = StringListFilter(method='filter_permissions')

    class Meta:
        model = User
        fields = ['email', 'is_active']

    def filter_role_not_in(self, queryset, name, value):
        roles = [USER_ROLE[role].value for role in value]
        return queryset.filter(
            ~models.Q(portfolios__role__in=roles)
        )

    def filter_monitoring_sub_region_in(self, queryset, name, value):
        return queryset.filter(
            portfolios__monitoring_sub_region__in=value
        )

    def filter_monitoring_sub_region_not_in(self, queryset, name, value):
        return queryset.filter(
            ~models.Q(portfolios__monitoring_sub_region__in=value)
        )

    def filter_role_in(self, queryset, name, value):
        roles = [USER_ROLE[role].value for role in value]
        return queryset.annotate(
            highest_user_role=Min('portfolios__role')
        ).filter(highest_user_role__in=roles)

    def filter_full_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.annotate(
            full=Coalesce(
                Lower('full_name'),
                Concat(Lower('first_name'), models.Value(' '), Lower('last_name')),
            )
        ).annotate(
            idx=StrIndex('full', models.Value(value.lower()))
        ).filter(full__unaccent__icontains=value).order_by('idx')

    def filter_include_inactive(self, queryset, name, value):
        if value is False:
            return queryset.filter(is_active=True)
        return queryset

    def filter_permissions(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(groups__permissions__codename__in=value)

    @property
    def qs(self):
        # to get the highest role
        return super().qs.prefetch_related('portfolios').distinct()


class PortfolioFilter(django_filters.FilterSet):
    role_in = StringListFilter(method='filter_role_in')

    class Meta:
        model = Portfolio
        fields = {
            'monitoring_sub_region': ['in'],
            'country': ['in'],
        }

    def filter_role_in(self, queryset, name, value):
        roles = [USER_ROLE[role].value for role in value]
        return queryset.filter(
            role__in=roles
        )


class ReviewerUserFilter(UserFilter):
    @property
    def qs(self):
        return super().qs.filter(
            groups__permissions__id=Permission.objects.get(codename='add_review').id
        )
