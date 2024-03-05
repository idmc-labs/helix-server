import django_filters

from utils.filters import StringListFilter, MultipleInputFilter, generate_type_for_filter_set
from apps.contrib.models import ExcelDownload, ClientTrackInfo, Client, BulkApiOperation
from apps.entry.models import ExternalApiDump
from apps.users.roles import USER_ROLE

from .enums import BulkApiOperationActionEnum, BulkApiOperationStatusEnum


class ExcelExportFilter(django_filters.FilterSet):
    status_list = StringListFilter(method='filter_status')

    class Meta:
        model = ExcelDownload
        fields = {
            'started_at': ['lt', 'gt', 'gte', 'lte']
        }

    def filter_status(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # internal filtering
                return qs.filter(status__in=value).distinct()
            # client side filtering
            return qs.filter(status__in=[
                ExcelDownload.EXCEL_GENERATION_STATUS.get(item).value for item in value
            ]).distinct()
        return qs

    @property
    def qs(self):
        return super().qs.filter(
            created_by=self.request.user
        )


class ClientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(method='filter_name')
    is_active = django_filters.BooleanFilter(method='filter_is_active')

    class Meta:
        model = Client
        fields = ()

    def filter_name(self, queryset, name, value):
        return queryset.filter(name__icontains=value)

    def filter_is_active(self, queryset, name, value):
        if value is True:
            return queryset.filter(is_active=True)
        if value is False:
            return queryset.filter(is_active=False)
        return queryset

    @property
    def qs(self):
        user = self.request.user
        if user.highest_role == USER_ROLE.ADMIN:
            return super().qs
        return super().qs.none()


class ClientTrackInfoFilter(django_filters.FilterSet):
    api_type = StringListFilter(method='filter_api_type')
    client_codes = StringListFilter(method='filter_client_codes')
    start_track_date = django_filters.DateFilter(method='filter_start_track_date')
    end_track_date = django_filters.DateFilter(method='filter_end_track_date')

    class Meta:
        model = ClientTrackInfo
        fields = ()

    def filter_api_type(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                return qs.filter(api_type__in=value).distinct()
            return qs.filter(api_type__in=[
                ExternalApiDump.ExternalApiType[item].value for item in value
            ]).distinct()
        return qs

    def filter_client_codes(self, qs, name, value):
        return qs.filter(client__code__in=value)

    def filter_start_track_date(self, qs, name, value):
        return qs.filter(tracked_date__gte=value)

    def filter_end_track_date(self, qs, name, value):
        return qs.filter(tracked_date__lte=value)

    @property
    def qs(self):
        user = self.request.user
        if user.highest_role == USER_ROLE.ADMIN:
            return super().qs.exclude(api_type='None').annotate(
                **ClientTrackInfo.annotate_api_name()
            ).select_related('client')
        return super().qs.none()


class BulkApiOperationFilter(django_filters.FilterSet):
    action_list = MultipleInputFilter(BulkApiOperationActionEnum, field_name='action')
    status_list = MultipleInputFilter(BulkApiOperationStatusEnum, field_name='status')

    class Meta:
        model = BulkApiOperation
        fields = []

    @property
    def qs(self):
        # TODO: SuperUser may also need to look at other's bulk operations
        return super().qs.filter(
            created_by=self.request.user,
        ).defer('success_list', 'failure_list')


ClientTrackInfoFilterDataType, ClientTrackInfoFilterDataInputType = generate_type_for_filter_set(
    ClientTrackInfoFilter,
    'contrib.schema.client_track_information_list',
    'ClientTrackInfoFilterDataType',
    'ClientTrackInfoFilterDataInputType',
)


ClientFilterDataType, ClientFilterDataInputType = generate_type_for_filter_set(
    ClientFilter,
    'contrib.schema.client_list',
    'ClientFilterDataType',
    'ClientFilterDataInputType',
)
