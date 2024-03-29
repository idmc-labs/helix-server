from collections import defaultdict
from django.db import models
from promise import Promise
from promise.dataloader import DataLoader
from apps.crisis.models import Crisis
from apps.country.models import Country, MonitoringSubRegion
from apps.entry.models import Figure


class TotalFigureThisYearByCountryCategoryEventTypeLoader(DataLoader):
    def __init__(
        self,
        *args,
        **kwargs
    ):
        self.category = kwargs.pop('category')
        self.event_type = kwargs.pop('event_type')
        return super().__init__(*args, **kwargs)

    def batch_load_fn(self, keys):
        '''
        keys: [countryId]
        '''

        qs = Country.objects.filter(
            id__in=keys
        ).annotate(
            **Country._total_figure_disaggregation_subquery()
        )

        if self.category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT:
            if self.event_type == Crisis.CRISIS_TYPE.CONFLICT:
                qs = qs.annotate(_total=models.F(Country.ND_CONFLICT_ANNOTATE))
            else:
                qs = qs.annotate(_total=models.F(Country.ND_DISASTER_ANNOTATE))
        else:
            if self.event_type == Crisis.CRISIS_TYPE.CONFLICT:
                qs = qs.annotate(_total=models.F(Country.IDP_CONFLICT_ANNOTATE))
            else:
                qs = qs.annotate(_total=models.F(Country.IDP_DISASTER_ANNOTATE))

        list_to_dict = {
            item['id']: item['_total']
            for item in qs.values('id', '_total')
        }

        return Promise.resolve([
            list_to_dict.get(country)
            for country in keys
        ])


class MonitoringSubRegionCountryCountLoader(DataLoader):
    def batch_load_fn(self, keys: list):
        qs = MonitoringSubRegion.objects.filter(
            id__in=keys
        ).annotate(
            country_count=models.Count('countries', distinct=True)
        ).values('id', 'country_count')
        return Promise.resolve([
            item['country_count']
            for item in qs
        ])


class MonitoringSubRegionCountryLoader(DataLoader):
    def batch_load_fn(self, keys: list):
        country_qs = Country.objects.filter(
            monitoring_sub_region__in=keys
        )
        _map = defaultdict(list)
        for item in country_qs:
            _map[item.monitoring_sub_region_id].append(item)
        return Promise.resolve([_map[key] for key in keys])
