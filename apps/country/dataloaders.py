from collections import defaultdict

from django.db import models
from promise import Promise
from promise.dataloader import DataLoader

from apps.country.models import ContextualAnalysis, Country, MonitoringSubRegion, Summary
from apps.crisis.models import Crisis
from apps.entry.models import Figure


class TotalFigureThisYearByCountryCategoryEventTypeLoader(DataLoader):
    def __init__(self, *args, **kwargs):
        self.category = kwargs.pop("category")
        self.event_type = kwargs.pop("event_type")
        return super().__init__(*args, **kwargs)

    def batch_load_fn(self, keys):
        """
        keys: [countryId]
        """

        qs = Country.objects.filter(id__in=keys).annotate(**Country._total_figure_disaggregation_subquery())

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

        list_to_dict = {item["id"]: item["_total"] for item in qs.values("id", "_total")}

        return Promise.resolve([list_to_dict.get(country) for country in keys])


class MonitoringSubRegionCountryCountLoader(DataLoader):
    def batch_load_fn(self, keys: list):
        qs = (
            MonitoringSubRegion.objects.filter(id__in=keys)
            .annotate(country_count=models.Count("countries", distinct=True))
            .values("id", "country_count")
        )
        return Promise.resolve([item["country_count"] for item in qs])


class MonitoringSubRegionCountryLoader(DataLoader):
    def batch_load_fn(self, keys: list):
        country_qs = Country.objects.filter(monitoring_sub_region__in=keys)
        _map = defaultdict(list)
        for item in country_qs:
            _map[item.monitoring_sub_region_id].append(item)
        return Promise.resolve([_map[key] for key in keys])


# --- N+1 fixes for countryList per-object resolvers (coverage follow-up) ---


class CountryLastSummaryLoader(DataLoader):
    # CountryType.last_summary = country.summaries.last(); Summary has no Meta.ordering, so
    # .last() returns the highest-pk row per country.
    def batch_load_fn(self, keys: list):
        qs = Summary.objects.filter(country_id__in=keys).order_by("country_id", "-id").distinct("country_id")
        _map = {s.country_id: s for s in qs}
        return Promise.resolve([_map.get(key) for key in keys])


class CountryLastContextualAnalysisLoader(DataLoader):
    # CountryType.last_contextual_analysis = country.contextual_analyses.last() (highest pk).
    def batch_load_fn(self, keys: list):
        qs = ContextualAnalysis.objects.filter(country_id__in=keys).order_by("country_id", "-id").distinct("country_id")
        _map = {c.country_id: c for c in qs}
        return Promise.resolve([_map.get(key) for key in keys])


class CountryMonitoringExpertLoader(DataLoader):
    # CountryType.monitoring_expert = Portfolio.objects.filter(country=self, role=MONITORING_EXPERT).first().
    # Portfolio.country is OneToOne, so at most one per country.
    def batch_load_fn(self, keys: list):
        from apps.users.enums import USER_ROLE
        from apps.users.models import Portfolio

        qs = Portfolio.objects.filter(country_id__in=keys, role=USER_ROLE.MONITORING_EXPERT)
        _map = {p.country_id: p for p in qs}
        return Promise.resolve([_map.get(key) for key in keys])


class MonitoringSubRegionRegionalCoordinatorLoader(DataLoader):
    # CountryType.regional_coordinator = country.monitoring_sub_region.regional_coordinator, i.e.
    # the REGIONAL_COORDINATOR Portfolio for the sub-region (<=1 per sub-region). Keyed by sub-region id.
    def batch_load_fn(self, keys: list):
        from apps.users.enums import USER_ROLE
        from apps.users.models import Portfolio

        qs = Portfolio.objects.filter(monitoring_sub_region_id__in=keys, role=USER_ROLE.REGIONAL_COORDINATOR)
        _map = {p.monitoring_sub_region_id: p for p in qs}
        return Promise.resolve([_map.get(key) for key in keys])
