import strawberry
from strawberry import auto
from .models import Country


@strawberry.django.ordering.order(Country)
class CountryOrder:
    id: auto
    iso3: auto
    iso2: auto
    name: auto
