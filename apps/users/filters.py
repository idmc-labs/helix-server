import django_filters
from django.contrib.auth.models import Permission
from django.db import models
from django.db.models import Min

from apps.users.enums import USER_ROLE
from apps.users.models import Portfolio, User
from utils.filters import IDFilter, IDListFilter, MultiWordSearchFilterSet, StringListFilter, generate_type_for_filter_set


class UserFilter(MultiWordSearchFilterSet):
    id = IDFilter(field_name="id", lookup_expr="exact")
    role_in = StringListFilter(method="filter_role_in")
    role_not_in = StringListFilter(method="filter_role_not_in")
    monitoring_sub_region_in = IDListFilter(method="filter_monitoring_sub_region_in")
    monitoring_sub_region_not_in = IDListFilter(method="filter_monitoring_sub_region_not_in")
    include_inactive = django_filters.BooleanFilter(method="filter_include_inactive")
    permissions = StringListFilter(method="filter_permissions")

    class Meta:
        model = User
        fields = ["is_active"]
        multi_word_search_fields = ["first_name", "last_name", "email"]

    def filter_role_not_in(self, queryset, name, value):
        roles = [USER_ROLE[role].value for role in value]
        return queryset.filter(~models.Q(portfolios__role__in=roles))

    def filter_monitoring_sub_region_in(self, queryset, name, value):
        return queryset.filter(portfolios__monitoring_sub_region__in=value)

    def filter_monitoring_sub_region_not_in(self, queryset, name, value):
        return queryset.filter(~models.Q(portfolios__monitoring_sub_region__in=value))

    def filter_role_in(self, queryset, name, value):
        roles = [USER_ROLE[role].value for role in value]
        return queryset.annotate(highest_user_role=Min("portfolios__role")).filter(highest_user_role__in=roles)

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
        return super().qs.prefetch_related("portfolios").distinct()


class PortfolioFilter(django_filters.FilterSet):
    role_in = StringListFilter(method="filter_role_in")

    class Meta:
        model = Portfolio
        fields = {
            "monitoring_sub_region": ["in"],
            "country": ["in"],
        }

    def filter_role_in(self, queryset, name, value):
        roles = [USER_ROLE[role].value for role in value]
        return queryset.filter(role__in=roles)


class ReviewerUserFilter(UserFilter):
    @property
    def qs(self):
        return super().qs.filter(groups__permissions__id=Permission.objects.get(codename="add_review").id)


UserFilterDataType, UserFilterDataInputType = generate_type_for_filter_set(
    UserFilter,
    "users.schema.users",
    "UserFilterDataType",
    "UserFilterDataInputType",
)
