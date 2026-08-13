from django.db.models import Exists, Max, Min, OuterRef, Subquery

from apps.contextualupdate.models import ContextualUpdate
from apps.country.models import Country
from apps.crisis.models import Crisis
from apps.organization.models import Organization
from utils.filters import AcceptsOrdering, MultiWordSearchFilterSet, StringListFilter


class ContextualUpdateFilter(AcceptsOrdering, MultiWordSearchFilterSet):
    countries = StringListFilter(method="filter_countries")
    sources = StringListFilter(method="filter_sources")
    publishers = StringListFilter(method="filter_publishers")
    crisis_types = StringListFilter(method="filter_crisis_types")

    class Meta:
        model = ContextualUpdate
        fields = {
            "publish_date": ["lte", "gte"],
        }
        multi_word_search_fields = ["article_title"]

    def filter_m2m(self, qs, field_name, value):
        if not value:
            return qs
        # M2M paths (countries/sources/publishers): test membership with a correlated
        # Exists on self so the join fan-out stays inside the subquery -> no .distinct().
        return qs.filter(Exists(ContextualUpdate.objects.filter(pk=OuterRef("pk"), **{f"{field_name}__in": value})))

    def filter_countries(self, qs, name, value):
        return self.filter_m2m(qs, "countries", value)

    def filter_sources(self, qs, name, value):
        return self.filter_m2m(qs, "sources", value)

    def filter_publishers(self, qs, name, value):
        return self.filter_m2m(qs, "publishers", value)

    def filter_crisis_types(self, qs, name, value):
        if value:
            return qs.filter(status__in=[Crisis.CRISIS_TYPE.get(each) for each in value])
        return qs

    @property
    def qs(self):
        queryset = super().qs

        # Denormalise each M2M sort key into a per-update scalar so the list stays one row
        # per update, aliased to the ordering token so order_by binds to the annotation
        # instead of re-traversing the M2M. A correlated subquery rather than the whole-table
        # CTE the large lists use: sorting needs the key for every filtered row before the
        # LIMIT, and on a table this small the per-row aggregate beats aggregating the whole
        # table to serve one page. Built only for the key actually sorted on. Min ascending /
        # Max descending: that is the related row the fan-out join sorted the update at (see
        # EventFilter.qs for the full reasoning).
        def m2m_sort_key(model, reverse_name, field, aggregate):
            return Subquery(
                model.objects.filter(**{reverse_name: OuterRef("pk")})
                .order_by()
                .values(reverse_name)
                .annotate(key=aggregate(field))
                .values("key")[:1]
            )

        for token, (model, reverse_name, field) in {
            "countries__idmc_short_name": (Country, "contextualupdate", "idmc_short_name"),
            "publishers__name": (Organization, "published_contextual_updates", "name"),
            "sources__name": (Organization, "sourced_contextual_updates", "name"),
        }.items():
            if token in self.ordering_fields:
                aggregate = Max if token in self.descending_ordering_fields else Min
                queryset = queryset.annotate(**{token: m2m_sort_key(model, reverse_name, field, aggregate)})
        return queryset
