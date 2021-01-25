from django_filters import rest_framework as df

from apps.parking_lot.models import ParkingLot
from utils.filters import StringListFilter


class ParkingLotFilter(df.FilterSet):
    status_in = StringListFilter(method='filter_status_in')
    # assigned_to_in = StringListFilter(field_name='assigned_to', lookup_expr='in')
    assigned_to_in = StringListFilter(method='filter_assigned_to')

    class Meta:
        model = ParkingLot
        fields = {
            'title': ['icontains'],
            'created_by': ['exact'],
        }

    def filter_status_in(self, queryset, name, value):
        if value:
            # map enum names to values
            return queryset.filter(status__in=[ParkingLot.PARKING_LOT_STATUS.get(each)
                                               for each in value])
        return queryset

    def filter_assigned_to(self, queryset, name, value):
        if value:
            return queryset.filter(assigned_to__in=value)
        return queryset

    @property
    def qs(self):
        return super().qs.distinct()
