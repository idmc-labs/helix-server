from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext
from django_filters import rest_framework as df

from apps.country.models import HouseholdSize
from apps.entry.models import (
    DisaggregatedAge,
    Figure,
    FigureLocation,
    FigureTag,
)
from utils.filters import IDFilter, MultiWordSearchFilterSet
from utils.permissions import PERMISSION_DENIED_MESSAGE


class FigureLocationFilter(df.FilterSet):
    class Meta:
        model = FigureLocation
        fields = ["country"]


class DisaggregatedAgeFilter(df.FilterSet):
    class Meta:
        model = DisaggregatedAge
        fields = {
            "sex": ["in"],
        }


class FigureFilter(df.FilterSet):
    class Meta:
        model = Figure
        fields = {
            "unit": ("exact",),
            "start_date": ("lte", "gte"),
        }


class FigureTagFilter(MultiWordSearchFilterSet):
    class Meta:
        model = FigureTag
        fields = []
        multi_word_search_fields = ["name"]


class HouseholdSizeAffectedFigureFilter(df.FilterSet):
    """Figures that would be affected by editing one AHHS row.

    A figure is affected when it is a recommended, household-unit figure in the same country,
    with a start date in the same year as the AHHS row.

    Each figure keeps its own copy of the household size, so some of these figures may have a
    different value from the AHHS row. The caller sees each figure's value and can sort on it.
    """

    household_size_id = IDFilter(method="filter_household_size_id")

    def filter_household_size_id(self, qs, name, value):
        ahhs = HouseholdSize.objects.filter(pk=value).first()
        if ahhs is None:
            return qs.none()
        return qs.filter(
            country=ahhs.country_id,
            start_date__year=ahhs.year,
            role=Figure.ROLE.RECOMMENDED,
            unit=Figure.UNIT.HOUSEHOLD,
        )

    @property
    def qs(self):
        # Only users who can edit AHHS can see this list.
        if not self.request.user.has_perm("country.change_householdsize"):
            raise PermissionDenied(gettext(PERMISSION_DENIED_MESSAGE))

        qs = super().qs

        # No AHHS row given: return nothing instead of every figure.
        if not self.form.cleaned_data.get("household_size_id"):
            return qs.none()
        return qs

    class Meta:
        model = Figure
        fields = []
