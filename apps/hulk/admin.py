from django.contrib import admin

from apps.hulk.models import HulkBulkImport, HulkBulkImportDataset


@admin.register(HulkBulkImport)
class HulkBulkImportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_by",
        "status",
        "created_at",
        "started_at",
        "completed_at",
        "celery_task_id",
        "celery_state",
    )
    list_filter = ("status",)
    readonly_fields = (
        "created_at",
        "started_at",
        "completed_at",
        "celery_task_id",
        "celery_state",
    )

    @admin.display(description="Celery state")
    def celery_state(self, obj: HulkBulkImport) -> str:
        # Best-effort lookup: Celery's result backend has a TTL (typically
        # one day), so finished tasks may report PENDING after expiry. This
        # is useful primarily for diagnosing rows that are stuck in
        # IN_PROGRESS — the on-row ``status`` is authoritative otherwise.
        if not obj.celery_task_id:
            return "-"
        try:
            from helix.celery import app as celery_app

            return celery_app.AsyncResult(obj.celery_task_id).state
        except Exception as exc:  # pragma: no cover - admin diagnostic only
            return f"error: {exc}"


admin.site.register(HulkBulkImportDataset)
