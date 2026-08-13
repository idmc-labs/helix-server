from django.db import models
from promise import Promise
from promise.dataloader import DataLoader

from apps.country.models import ContextualAnalysis, Country, MonitoringSubRegion, Summary


class TotalFigureThisYearByCountryLoader(DataLoader):
    """The four current-year figure totals of a country: (ND, IDP) x (conflict, disaster).

    One grouped pass over the figure table carries all four, so the four fields share one
    loader — and one query. The values match `_total_figure_disaggregation_subquery` in its
    default current-year unfiltered scope, which is the only scope that reaches a loader:
    `CountryType` reads an annotation whenever the list built one (aggregate figures, or a
    sort by a total).
    """

    TOTAL_FIELDS = (
        Country.ND_CONFLICT_ANNOTATE,
        Country.ND_DISASTER_ANNOTATE,
        Country.IDP_CONFLICT_ANNOTATE,
        Country.IDP_DISASTER_ANNOTATE,
    )

    def batch_load_fn(self, keys):
        """
        keys: [countryId]
        """
        qs = Country.annotate_total_figure_disaggregation_via_cte(Country.objects.filter(id__in=keys)).values(
            "id", *self.TOTAL_FIELDS
        )
        totals_by_country = {row["id"]: {field: row[field] for field in self.TOTAL_FIELDS} for row in qs}
        # A country the filter did not return has no total of any kind.
        missing = {field: None for field in self.TOTAL_FIELDS}

        return Promise.resolve([totals_by_country.get(country, missing) for country in keys])


class MonitoringSubRegionCountryCountLoader(DataLoader):
    def batch_load_fn(self, keys: list):
        qs = (
            MonitoringSubRegion.objects.filter(id__in=keys)
            .annotate(country_count=models.Count("countries", distinct=True))
            .values("id", "country_count")
        )
        _map = {item["id"]: item["country_count"] for item in qs}
        return Promise.resolve([_map.get(key, 0) for key in keys])


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
