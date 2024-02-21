from django.contrib import admin
from django.utils.safestring import mark_safe
from django.conf import settings
from admin_auto_filters.filters import AutocompleteFilterFactory

from utils.common import return_error_as_string
from apps.contrib.models import (
    Client,
    ClientTrackInfo,
    ExcelDownload,
    BulkApiOperation,
)


class ReadOnlyMixin():
    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False


class ClientAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'name', 'code', 'created_at', 'modified_at',
    ]
    autocomplete_fields = ('created_by', 'last_modified_by',)
    search_fields = ['code', 'name']

    def save_model(self, request, obj, form, change):
        if obj.id is not None:
            obj.last_modified_by = request.user
        else:
            obj.created_by = request.user
        obj.save()


class ClientTrackInfoAdmin(admin.ModelAdmin):
    list_display = ['id', 'api_type', 'client_name', 'requests_per_day', 'tracked_date']
    autocomplete_fields = ('client',)
    search_fields = ['client__code', 'client__name']
    list_display_links = ['id']

    def client_name(self, obj):
        return obj.client.name

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('client',)


class ExcelDownloadAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'download_type',
        'status',
        'created_by',
        'file',
        'file_size',
        'started_at',
        'completed_at',
    ]
    autocomplete_fields = ('created_by',)
    list_filter = ('download_type',)
    list_display_links = ['id']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')


@admin.register(BulkApiOperation)
class BulkApiOperationAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = [
        'id',
        'created_at',
        'created_by',
        'action',
        'status',
        'success_count',
        'failure_count',
    ]
    autocomplete_fields = ('created_by',)
    list_filter = (
        'action',
        'status',
        AutocompleteFilterFactory('User', 'created_by'),
    )
    list_display_links = ['id']
    readonly_fields = (
        'success_list_preview',
        'failure_list_preview',
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')

    @return_error_as_string
    def success_list_preview(self, obj: BulkApiOperation):
        header = ""
        rows = ""
        if obj.action == BulkApiOperation.BULK_OPERATION_ACTION.FIGURE_EVENT:
            header = """
                  <tr>
                    <th>Figure ID</th>
                    <th>URL</th>
                  </tr>
            """
            rows = ""
            for success in obj.success_list:
                url = settings.FRONTEND_BASE_URL + success["frontend_url"]
                rows += (f'''
                    <tr>
                      <td>{success["id"]}</td>
                      <td><a href={url} target="_blank">{url}</a></td>
                    </tr>
                ''')
        return mark_safe(f"<table>{header}{rows}</table>")

    @return_error_as_string
    def failure_list_preview(self, obj: BulkApiOperation):
        def _errors_to_str(errors):
            try:
                _errors = []
                for error in errors:
                    if type(error) is list:
                        _errors.append(_errors_to_str(error))
                    else:
                        _errors.append(
                            ": ".join([error['field'], error['messages']])
                        )
                return "</br>".join(_errors)
            except Exception:
                return str(errors)

        header = ""
        rows = ""
        if obj.action == BulkApiOperation.BULK_OPERATION_ACTION.FIGURE_EVENT:
            header = """
                  <tr>
                    <th>Figure ID</th>
                    <th>URL</th>
                    <th>Errors</th>
                    <th style="width:10%">Errors (Raw)</th>
                  </tr>
            """
            rows = ""
            for failure in obj.failure_list:
                url = settings.FRONTEND_BASE_URL + failure["frontend_url"]
                errors = _errors_to_str(failure["errors"])
                rows += (f'''
                    <tr>
                      <td>{failure["id"]}</td>
                      <td><a href={url} target="_blank">{url}</a></td>
                      <td>{errors}</td>
                      <td>{failure["errors"]}</td>
                    </tr>
                ''')
        return mark_safe(f"<table>{header}{rows}</table>")


admin.site.register(Client, ClientAdmin)
admin.site.register(ClientTrackInfo, ClientTrackInfoAdmin)
admin.site.register(ExcelDownload, ExcelDownloadAdmin)
