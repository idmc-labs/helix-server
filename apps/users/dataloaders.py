from promise import Promise
from promise.dataloader import DataLoader

from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models

from apps.users.models import Portfolio, USER_ROLE


PORTFOLIO_ROLES_ORDER = [
    USER_ROLE.REGIONAL_COORDINATOR,
    USER_ROLE.MONITORING_EXPERT,
]


class UserPortfoliosMetadataLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = Portfolio.objects.filter(
            user__in=keys,
        ).order_by().values('user').annotate(
            portfolio_roles=ArrayAgg(models.F('role'), distinct=True),
        ).values_list('user_id', 'portfolio_roles')

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
                'is_admin': USER_ROLE.ADMIN.value in portfolio_roles,
                'is_directors_office': USER_ROLE.DIRECTORS_OFFICE.value in portfolio_roles,
                'is_reporting_team': USER_ROLE.REPORTING_TEAM.value in portfolio_roles,
                'portfolio_role': portfolio_role,
                'portfolio_role_display': portfolio_role_display,
            }

        return Promise.resolve([
            _map[key] for key in keys
        ])
