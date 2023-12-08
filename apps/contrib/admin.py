from django.contrib import admin
from apps.contrib.models import Client, ClientTrackInfo, ExcelDownload


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
    list_filter = ['download_type']
    list_display_links = ['id']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')


admin.site.register(Client, ClientAdmin)
admin.site.register(ClientTrackInfo, ClientTrackInfoAdmin)
admin.site.register(ExcelDownload, ExcelDownloadAdmin)
