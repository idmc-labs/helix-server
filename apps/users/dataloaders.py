from promise.dataloader import DataLoader
from apps.users.models import User, USER_ROLE
from django.db.models import Case, When, IntegerField
from promise import Promise


class UserPortfolioRoleLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = User.objects.filter(
            id__in=keys
        ).annotate(
            portfolio_role=Case(
                When(
                    portfolios__role__in=[USER_ROLE.REGIONAL_COORDINATOR.value],
                    then=USER_ROLE.REGIONAL_COORDINATOR.value
                ),
                When(
                    portfolios__role__in=[USER_ROLE.MONITORING_EXPERT.value],
                    then=USER_ROLE.MONITORING_EXPERT.value
                ),
                default=USER_ROLE.GUEST.value,
                output_field=IntegerField(),
            )
        ).values('id', 'portfolio_role')
        batch_load = {
            item['id']: USER_ROLE(item['portfolio_role']).label
            for item in qs
        }
        return Promise.resolve([
            batch_load.get(key) for key in keys
        ])
