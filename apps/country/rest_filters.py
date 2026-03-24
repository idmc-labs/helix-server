import django_filters

from apps.country.models import HouseholdSize
from utils.common import get_name_choices


class RestHouseholdSizeFilterSet(django_filters.FilterSet):
    gap_filling_method = django_filters.ChoiceFilter(
        choices=get_name_choices(HouseholdSize.GAP_FILLING_METHOD),
    )

    class Meta:
        model = HouseholdSize
        fields = {"size": ["exact"], "year": ["exact"], "source": ["unaccent__icontains"]}
