import django_filters
from django.contrib.auth.models import Permission
from django.db import models
from django.db.models import Min

from apps.users.enums import USER_ROLE
from apps.users.models import Portfolio, User
from utils.filters import IDFilter, IDListFilter, MultiWordSearchFilterSet, StringListFilter, generate_type_for_filter_set
from utils.graphene.ordering import strip_direction


class UserFilter(MultiWordSearchFilterSet):
    # The role booleans are computed per user from their portfolios (see
    # UserPortfolioMetaDataLoader), so there is no column to ORDER BY. Take the active
    # ordering so they can be annotated on demand — they are Exists subqueries, and the
    # default user list has no reason to pay for three of them.
    accepts_ordering = True

    id = IDFilter(field_name="id", lookup_expr="exact")
    email = django_filters.CharFilter(field_name="email", lookup_expr="iexact")
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

    # Mirrors UserPortfolioMetaDataLoader: each flag is "does this user hold a portfolio with
    # that role". Exists rather than a join so the annotation cannot multiply user rows on a
    # list that already carries to-many portfolio filters.
    ROLE_FLAG_ANNOTATIONS = {
        "is_admin": USER_ROLE.ADMIN,
        "is_directors_office": USER_ROLE.DIRECTORS_OFFICE,
        "is_reporting_team": USER_ROLE.REPORTING_TEAM,
    }

    def __init__(self, *args, ordering=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ordering_fields = {strip_direction(field) for field in ordering.split(",") if field} if ordering else set()

    @property
    def qs(self):
        # No prefetch_related("portfolios"): UserType serves portfolios via its own resolver,
        # not off the instance, so the eager prefetch was a dead load. The .distinct() stays —
        # it is load-bearing for the to-many portfolio filters (see FUTURE_WORK).
        queryset = super().qs.distinct()
        annotations = {
            flag: models.Exists(Portfolio.objects.filter(user=models.OuterRef("pk"), role=role.value))
            for flag, role in self.ROLE_FLAG_ANNOTATIONS.items()
            if flag in self.ordering_fields
        }
        if annotations:
            queryset = queryset.annotate(**annotations)
        return queryset


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
