import strawberry
from strawberry import auto
from django.db.models import Q
from apps.country.models import Country
from .models import (
    Conflict,
    Disaster,
)
from typing import List


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


@strawberry.django.filters.filter(Conflict, lookups=True)
class ConflictFilter:
    id: auto


@strawberry.django.filters.filter(Disaster, lookups=True)
class DisasterFilter:
    id: auto


@strawberry.django.filters.filter(Conflict, lookups=True)
class ConflictStatisticsFilter:
    countries: List[strawberry.ID] | None
    start_year: int | None
    end_year: int | None
    countries_iso3: List[str] | None

    def filter_start_year(self, queryset):
        if not self.start_year:
            return queryset
        return queryset.filter(year__gte=self.start_year)

    def filter_end_year(self, queryset):
        if not self.end_year:
            return queryset
        return queryset.filter(year__lte=self.end_year)

    def filter_countries_iso3(self, queryset):
        if not self.countries_iso3:
            return queryset
        return queryset.filter(country__iso3__in=self.countries_iso3)


@strawberry.django.filters.filter(Disaster, lookups=True)
class DisasterStatisticsFilter:
    categories: List[str] | None
    countries: List[strawberry.ID] | None
    start_year: int | None
    end_year: int | None
    countries_iso3: List[str] | None

    def filter_categories(self, queryset):
        if not self.categories:
            return queryset
        return queryset.filter(hazard_type__in=self.categories)

    def filter_start_year(self, queryset):
        if not self.start_year:
            return queryset
        return queryset.filter(year__gte=self.start_year)

    def filter_end_year(self, queryset):
        if not self.end_year:
            return queryset
        return queryset.filter(year__lte=self.end_year)

    def filter_countries_iso3(self, queryset):
        if not self.countries_iso3:
            return queryset
        return queryset.filter(iso3__overlap=self.countries_iso3)
