from datetime import datetime

from django.db.models import Sum
from promise import Promise
from promise.dataloader import DataLoader


class TotalFigureThisYearByCountryCategoryLoader(DataLoader):
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
        from apps.entry.models import Figure, FigureCategory

        queryset = Figure.objects.fitler(
            country__in=keys,
            role=Figure.ROLE.RECOMMENDED,
        )
        this_year = datetime.today().year

        if self.category == FigureCategory.flow_new_displacement_id():
            qs = Figure.filtered_nd_figures(
                queryset,
                start_date=datetime(
                    year=this_year,
                    month=1,
                    day=1
                ),
                end_date=datetime(
                    year=this_year,
                    month=12,
                    day=31
                )
            )
        elif self.category == FigureCategory.stock_idp_id():
            qs = Figure.filtered_idp_figures(
                queryset,
                end_date=datetime(
                    year=this_year,
                    month=12,
                    day=31
                )
            )

        qs = qs.order_by().values(
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
