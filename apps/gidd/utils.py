import typing
from collections import OrderedDict

from django.db.models import Case, F, IntegerField, Q, QuerySet, Sum, When
from django.db.models.functions import ExtractYear

from apps.entry.models import Figure


def _sum_by_category(category: int) -> Sum:
    return Sum(
        Case(
            When(category=category, then=F("total_figures")),
            output_field=IntegerField(),
        )
    )


def displacement_aggregates(years: typing.Optional[typing.Iterable[int]] = None) -> QuerySet:
    """
    Aggregate recommended new displacement and year-end IDP figures by year, country, and cause.
    Optionally filter results by years.
    """
    nd = Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT
    idps = Figure.FIGURE_CATEGORY_TYPES.IDPS
    qs = (
        Figure.objects.filter(role=Figure.ROLE.RECOMMENDED, start_date__isnull=False)
        .filter(Q(category=nd) | Q(category=idps, end_date__month=12, end_date__day=31))
        .annotate(year=ExtractYear("end_date"))
    )
    if years is not None:
        qs = qs.filter(year__in=years)
    # NOTE: Use country's short name to keep export labels consistent with the GIDD release and event type as the cause
    # since displacement is reported at the event level rather than by the figure's cause.
    return (
        qs.values(
            "year",
            iso3=F("country__iso3"),
            country_name=F("country__idmc_short_name"),
            cause=F("event__event_type"),
        )
        .annotate(
            new_displacement=_sum_by_category(nd),
            total_displacement=_sum_by_category(idps),
        )
        .order_by("iso3", "year", "cause")
    )

