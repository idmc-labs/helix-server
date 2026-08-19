from admin_auto_filters.filters import AutocompleteFilterFactory
from django import forms
from django.conf import settings
from django.contrib import admin
from django.utils.safestring import mark_safe
from django_celery_beat.admin import PeriodicTaskAdmin
from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)

from apps.contrib.models import (
    BulkApiOperation,
    Client,
    ClientTrackInfo,
    ExcelDownload,
)
from utils.common import return_error_as_string


class ReadOnlyMixin:
    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False


class ClientAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "code",
        "created_at",
        "modified_at",
    ]
    autocomplete_fields = (
        "created_by",
        "last_modified_by",
    )
    search_fields = ["code", "name"]

    def save_model(self, request, obj, form, change):
        if obj.id is not None:
            obj.last_modified_by = request.user
        else:
            obj.created_by = request.user
        obj.save()


class ClientTrackInfoAdmin(admin.ModelAdmin):
    list_display = ["id", "api_type", "client_name", "requests_per_day", "tracked_date"]
    autocomplete_fields = ("client",)
    search_fields = ["client__code", "client__name"]
    list_display_links = ["id"]

    def client_name(self, obj):
        return obj.client.name

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "client",
            )
        )


class ExcelDownloadAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "download_type",
        "status",
        "created_by",
        "file",
        "file_size",
        "started_at",
        "completed_at",
    ]
    autocomplete_fields = ("created_by",)
    list_filter = ("download_type",)
    list_display_links = ["id"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("created_by")


@admin.register(BulkApiOperation)
class BulkApiOperationAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = [
        "id",
        "created_at",
        "created_by",
        "action",
        "status",
        "success_count",
        "failure_count",
    ]
    autocomplete_fields = ("created_by",)
    list_filter = (
        "action",
        "status",
        AutocompleteFilterFactory("User", "created_by"),
    )
    list_display_links = ["id"]
    readonly_fields = (
        "success_list_preview",
        "failure_list_preview",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("created_by")

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
                rows += f"""
                    <tr>
                      <td>{success["id"]}</td>
                      <td><a href={url} target="_blank">{url}</a></td>
                    </tr>
                """
        return mark_safe(f"<table>{header}{rows}</table>")

    @return_error_as_string
    def failure_list_preview(self, obj: BulkApiOperation):
        def _errors_to_str(errors):
            try:
                _errors = []
                for error in errors:
                    if isinstance(error, list):
                        _errors.append(_errors_to_str(error))
                    else:
                        _errors.append(": ".join([error["field"], error["messages"]]))
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
                rows += f"""
                    <tr>
                      <td>{failure["id"]}</td>
                      <td><a href={url} target="_blank">{url}</a></td>
                      <td>{errors}</td>
                      <td>{failure["errors"]}</td>
                    </tr>
                """
        return mark_safe(f"<table>{header}{rows}</table>")


admin.site.register(Client, ClientAdmin)
admin.site.register(ClientTrackInfo, ClientTrackInfoAdmin)
admin.site.register(ExcelDownload, ExcelDownloadAdmin)


# django_celery_beat's own admin, narrowed to the enable/disable switch. Schedules
# come from `helix.celery.app.conf.beat_schedule` and are rewritten on every beat
# start, so anything editable here other than `enabled` would be silently reverted.
# The schedule models are unregistered for the same reason.
for _model in (ClockedSchedule, CrontabSchedule, IntervalSchedule, SolarSchedule, PeriodicTask):
    admin.site.unregister(_model)


@admin.register(PeriodicTask)
class HelixPeriodicTaskAdmin(PeriodicTaskAdmin):
    # PeriodicTaskForm expects an editable `task` field; every field but `enabled`
    # is read-only here, so a plain ModelForm is used instead.
    form = forms.ModelForm
    change_form_template = None
    date_hierarchy = None
    list_display = ("name", "task", "enabled", "schedule", "last_run_at", "total_run_count")
    list_display_links = ("name",)
    list_editable = ("enabled",)
    list_filter = ("enabled",)
    actions = ("enable_tasks", "disable_tasks", "run_tasks")
    fieldsets = (
        (None, {"fields": ("name", "task", "enabled", "schedule", "args", "kwargs")}),
        ("Last run", {"fields": ("last_run_at", "total_run_count")}),
    )
    readonly_fields = (
        "name",
        "task",
        "schedule",
        "args",
        "kwargs",
        "last_run_at",
        "total_run_count",
    )

    @admin.display(description="Schedule")
    def schedule(self, obj):
        if obj.crontab_id:
            return obj.crontab.human_readable
        return obj.interval or obj.solar or obj.clocked

    def get_actions(self, request):
        # The inherited actions declare no `permissions`, so Django offers them to
        # anyone who can open the changelist. All three of them write to a task or
        # fire it, so they need the change permission.
        if not self.has_change_permission(request):
            return {}
        return super().get_actions(request)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        # Skips PeriodicTaskAdmin's crontab-picker context, which belongs to the
        # template this admin drops.
        return admin.ModelAdmin.changeform_view(self, request, object_id, form_url, extra_context)
