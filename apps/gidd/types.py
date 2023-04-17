# types.py
import strawberry
import datetime
from strawberry import auto, ID
from apps.country.models import Country
from .models import (
    Conflict,
    Disaster,
)
from .gh_filters import (
    CountryFilter,
    ConflictFilter,
    DisasterFilter,
)
from typing import List, Optional


@strawberry.type
class TimeSeriesStatisticsType:
    year: str
    total: int


@strawberry.type
class DisasterCountryType:
    id: ID
    iso3: str
    country_name: str


@strawberry.type
class DisasterTimeSeriesStatisticsType:
    year: str
    total: int


@strawberry.type
class CategoryStatisticsType:
    label: str
    total: int


@strawberry.type
class ConflictStatisticsType:
    new_displacements: int
    total_idps: int
    new_displacement_timeseries: List[TimeSeriesStatisticsType]
    idps_timeseries: List[TimeSeriesStatisticsType]


@strawberry.type
class DisasterStatisticsType:
    new_displacements: int
    total_events: int
    timeseries: List[DisasterTimeSeriesStatisticsType]
    categories: List[CategoryStatisticsType]


@strawberry.type
class FigureAnalysisType:
    id: strawberry.ID
    year: int
    nd_figures: int
    nd_methodology_and_sources: str
    nd_caveats_and_challenges: str
    idp_figures: int
    idp_methodology_and_sources: str
    idp_caveats_and_challenges: str
    created_at: datetime.date
    updated_at: datetime.date


@strawberry.django.type(Country)
class CountryType:
    id: auto
    iso3: auto
    iso2: auto
    name: auto
    bounding_box: List[float]
    centroid: List[float]
    idmc_short_name: Optional[str]
    idmc_full_name: Optional[str]
    country_code: Optional[int]


@strawberry.django.type(Country, pagination=True, filters=CountryFilter)
class CountryListType(CountryType):
    pass


@strawberry.django.type(Conflict)
class ConflictType:
    id: auto
    year: auto
    total_displacement: auto
    new_displacement: auto
    country_name: auto
    iso3: auto


@strawberry.django.type(Conflict, pagination=True, filters=ConflictFilter)
class ConflictListType(ConflictType):
    pass


@strawberry.django.type(Disaster)
class DisasterType:
    id: auto
    year: auto
    event: auto
    start_date: auto
    start_date_accuracy: auto
    end_date: auto
    end_date_accuracy: auto
    hazard_category: auto
    hazard_sub_category: auto
    hazard_sub_type: auto
    hazard_type: auto
    new_displacement: auto
    country_names: List[str]
    iso3: List[str]


@strawberry.django.type(Disaster, pagination=True, filters=DisasterFilter)
class DisasterListType(DisasterType):
    pass
