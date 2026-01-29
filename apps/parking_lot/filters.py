from apps.parking_lot.models import ParkedItem
from utils.filters import MultiWordSearchFilterSet, StringListFilter


class ParkingLotFilter(MultiWordSearchFilterSet):
    status_in = StringListFilter(method="filter_status_in")
    assigned_to_in = StringListFilter(method="filter_assigned_to")

    class Meta:
        model = ParkedItem
        fields = {
            "created_by": ["exact"],
        }
        search_fields = ["title"]

    def filter_status_in(self, queryset, name, value):
        if value:
            # map enum names to values
            return queryset.filter(status__in=[ParkedItem.PARKING_LOT_STATUS.get(each) for each in value])
        return queryset

    def filter_assigned_to(self, queryset, name, value):
        if value:
            return queryset.filter(assigned_to__in=value)
        return queryset

    @property
    def qs(self):
        return super().qs.distinct()
