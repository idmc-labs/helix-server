from datetime import datetime

from django.db.models import Sum
from promise import Promise
from promise.dataloader import DataLoader


class TotalFigureByCountryCategoryLoader(DataLoader):
    def __init__(
        self,
        *args,
        **kwargs
    ):
        self.category = kwargs.pop('category')
        return super().__init__(*args, **kwargs)

    def batch_load_fn(self, keys):
        '''
        keys: [countryId]
        '''
        from apps.entry.models import Figure

        qs = Figure.objects.filter(
            country__in=keys,
            role=Figure.ROLE.RECOMMENDED,
            category=self.category,
            end_date__year=datetime.today().year,
        ).order_by().values(
            'country'
        ).annotate(
            _total=Sum('total_figures')
        ).values('country', '_total')

        list_to_dict = {
            item['country']: item['_total']
            for item in qs
        }

        return Promise.resolve([
            list_to_dict.get(country, 0)
            for country in keys
        ])
