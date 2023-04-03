import strawberry
from strawberry import auto
from django.db.models import Q
from .models import Country


@strawberry.django.filters.filter(Country, lookups=True)
class CountryFilter:
    id: auto
    iso3: auto
    name: auto
    search: str | None

    def filter_search(self, queryset):
        if not self.search:
            return queryset
        return queryset.filter(
            Q(name__icontains=self.search) |
            Q(iso3__icontains=self.search)
        )
