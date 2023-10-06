from promise import Promise
from promise.dataloader import DataLoader

from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models

from apps.users.models import Portfolio, USER_ROLE


class UserPortfolioRoleLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = Portfolio.objects.filter(
            user__in=keys,
        ).order_by().values('user').annotate(
            portfolio_roles=ArrayAgg(models.F('role'), distinct=True),
        ).annotate(
            portfolio_role=models.Case(
                models.When(
                    portfolio_roles__overlap=[USER_ROLE.REGIONAL_COORDINATOR.value],
                    then=USER_ROLE.REGIONAL_COORDINATOR.value
                ),
                models.When(
                    portfolio_roles__overlap=[USER_ROLE.MONITORING_EXPERT.value],
                    then=USER_ROLE.MONITORING_EXPERT.value
                ),
                default=USER_ROLE.GUEST.value,
                output_field=models.IntegerField(),
            ),
        ).values_list('user', 'portfolio_role')
        batch_load = {
            user: USER_ROLE(portfolio_role)
            for user, portfolio_role in qs
        }
        return Promise.resolve([
            batch_load.get(key) for key in keys
        ])
