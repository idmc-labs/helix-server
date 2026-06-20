from django.db.models import Exists, OuterRef

from apps.contextualupdate.models import ContextualUpdate
from apps.crisis.models import Crisis
from utils.filters import MultiWordSearchFilterSet, StringListFilter


class ContextualUpdateFilter(MultiWordSearchFilterSet):
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
