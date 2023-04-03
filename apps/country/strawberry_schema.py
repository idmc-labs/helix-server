import strawberry
from typing import List, Optional
from asgiref.sync import sync_to_async

from .models import Country
from .strawberry_filters import CountryFilter
from .strawberry_order import CountryOrder


@strawberry.django.type(Country)
class CountryType:
    id: strawberry.auto
    iso3: strawberry.auto
    iso2: strawberry.auto
    name: strawberry.auto
    idmc_full_name: strawberry.auto


@sync_to_async
def get_country_object(pk, iso3):
    if pk:
        return Country.objects.get(pk=pk)
    if iso3:
        return Country.objects.get(iso3=iso3)


@strawberry.type
class Query:
    @strawberry.field
    def country(self, pk: Optional[strawberry.ID] = None, iso3: Optional[str] = None) -> CountryType:
        return get_country_object(pk, iso3)

    countries: List[CountryType] = strawberry.django.field(
        filters=CountryFilter,
        order=CountryOrder,
        pagination=True,
    )
