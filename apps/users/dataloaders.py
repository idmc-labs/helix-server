from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models
from promise import Promise
from promise.dataloader import DataLoader

from apps.users.models import USER_ROLE, Portfolio

PORTFOLIO_ROLES_ORDER = [
    USER_ROLE.REGIONAL_COORDINATOR,
    USER_ROLE.MONITORING_EXPERT,
]


class UserPortfoliosMetadataLoader(DataLoader):
    """
    DataLoader for aggregating user portfolio metadata.

    This loader batches and caches the loading of user portfolio roles from the database,
    minimizing the number of queries needed to fetch user portfolio data across different requests.
    """

    def batch_load_fn(self, keys):
        qs = (
            Portfolio.objects.filter(
                user__in=keys,
            )
            .order_by()
            .values("user")
            .annotate(
                portfolio_roles=ArrayAgg(models.F("role"), distinct=True),
            )
            .values_list("user_id", "portfolio_roles")
        )

        _map = {}
        for user_id, portfolio_roles in qs:
            portfolio_role = USER_ROLE.GUEST.value
            portfolio_role_display = USER_ROLE.GUEST.label
            for role in PORTFOLIO_ROLES_ORDER:
                if role in portfolio_roles:
                    portfolio_role = role.value
                    portfolio_role_display = role.label
                    break

            _map[user_id] = {
                "is_admin": USER_ROLE.ADMIN.value in portfolio_roles,
                "is_directors_office": USER_ROLE.DIRECTORS_OFFICE.value in portfolio_roles,
                "is_reporting_team": USER_ROLE.REPORTING_TEAM.value in portfolio_roles,
                "portfolio_role": portfolio_role,
                "portfolio_role_display": portfolio_role_display,
            }

        return Promise.resolve(
            [
                # For default, using GUEST role
                _map.get(
                    key,
                    {
                        "is_admin": False,
                        "is_directors_office": False,
                        "is_reporting_team": False,
                        "portfolio_role": USER_ROLE.GUEST.value,
                        "portfolio_role_display": USER_ROLE.GUEST.label,
                    },
                )
                for key in keys
            ]
        )
