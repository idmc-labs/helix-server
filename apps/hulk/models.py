import typing
from uuid import uuid4

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from utils.fields import CachedFileField


def upload_dataset_import_file(instance, filename: str) -> str:
    return (
        f"hulk/bulk-operation/{instance.bulk_import_id}/datasets/"
        f"{instance.import_type.name.lower() if hasattr(instance.import_type, 'name') else instance.import_type}/import/"
        f"{uuid4()}/{filename}"
    )


def upload_dataset_success_file(instance, filename: str) -> str:
    return (
        f"hulk/bulk-operation/{instance.bulk_import_id}/datasets/"
        f"{instance.import_type.name.lower() if hasattr(instance.import_type, 'name') else instance.import_type}/success/"
        f"{uuid4()}/{filename}"
    )


def upload_dataset_failure_file(instance, filename: str) -> str:
    return (
        f"hulk/bulk-operation/{instance.bulk_import_id}/datasets/"
        f"{instance.import_type.name.lower() if hasattr(instance.import_type, 'name') else instance.import_type}/failure/"
        f"{uuid4()}/{filename}"
    )


# Resource types handled by the bulk pipeline. The order is *also* the
# dependency order the handler walks — later types reference earlier ones
# by UUID. Driver code should always iterate in this order.
HULK_BULK_RESOURCES = (
    "attachments",
    "source_previews",
    "entries",
    "events",
    "figures",
)


class HulkBulkImport(models.Model):
    WAIT_TIME_THRESHOLD_IN_MINUTES = 5
    """
    Maximum wait time (in minutes) for the bulk import to start.
    Helps prevent a large backlog if workers are down.
    """

    class HULK_BULK_IMPORT_STATUS(enum.Enum):
        PENDING = 0
        IN_PROGRESS = 1
        COMPLETED = 2
        FAILED = 3
        SKIPPED = 4

    created_at = models.DateTimeField(verbose_name=_("Created At"), auto_now_add=True)
    created_by = models.ForeignKey(
        "users.User",
        verbose_name=_("Created By"),
        related_name="created_%(class)s",
        on_delete=models.PROTECT,
    )

    # Runtime information
    started_at = models.DateTimeField(verbose_name=_("Started At"), null=True, blank=True)
    completed_at = models.DateTimeField(verbose_name=_("Completed At"), null=True, blank=True)
    # Celery task id assigned at dispatch time. Used by admins to verify
    # whether an IN_PROGRESS row is still being worked on (via AsyncResult)
    # or has been orphaned by a dead worker.
    celery_task_id = models.CharField(max_length=255, blank=True, null=True)

    # System generated fields
    status = enum.EnumField(
        enum=HULK_BULK_IMPORT_STATUS,
        default=HULK_BULK_IMPORT_STATUS.PENDING,
    )

    # Type hints
    get_action_display: typing.Callable
    get_status_display: typing.Callable
    datasets: "models.Manager[HulkBulkImportDataset]"

    class Meta:
        permissions = (("trigger_hulkbulkimport", "Can trigger hulk bulk import"),)

    def __str__(self):
        return f"HulkBulkImport-{self.pk}"

    def update_status(self, status: HULK_BULK_IMPORT_STATUS, commit=True):
        update_fields = ["status"]
        if status != self.status:
            if status == self.HULK_BULK_IMPORT_STATUS.IN_PROGRESS:
                self.started_at = timezone.now()
                update_fields.append("started_at")
            elif status in (
                self.HULK_BULK_IMPORT_STATUS.COMPLETED,
                self.HULK_BULK_IMPORT_STATUS.FAILED,
                self.HULK_BULK_IMPORT_STATUS.SKIPPED,
            ):
                self.completed_at = timezone.now()
                update_fields.append("completed_at")
        self.status = status
        if commit:
            self.save(update_fields=update_fields)


class HulkBulkImportDataset(models.Model):
    """
    One row per resource type uploaded for a HulkBulkImport. Stores the input
    JSONL plus the success/failure output JSONLs and per-type counts.

    Replaces the older 15-FileField layout on ``HulkBulkImport`` itself.
    """

    class HULK_BULK_IMPORT_DATASET_IMPORT_TYPE(enum.Enum):
        ATTACHMENT = 0
        SOURCE_PREVIEW = 1
        ENTRY = 2
        EVENT = 3
        FIGURE = 4

    bulk_import = models.ForeignKey(
        "hulk.HulkBulkImport",
        verbose_name=_("Bulk Import"),
        related_name="datasets",
        on_delete=models.CASCADE,
    )
    import_type = enum.EnumField(enum=HULK_BULK_IMPORT_DATASET_IMPORT_TYPE)

    import_file = CachedFileField(
        verbose_name=_("Import JSONL"),
        upload_to=upload_dataset_import_file,
        max_length=2000,
    )
    success_file = CachedFileField(
        verbose_name=_("Success JSONL"),
        blank=True,
        null=True,
        upload_to=upload_dataset_success_file,
        max_length=2000,
    )
    failure_file = CachedFileField(
        verbose_name=_("Failure JSONL"),
        blank=True,
        null=True,
        upload_to=upload_dataset_failure_file,
        max_length=2000,
    )

    success_count = models.PositiveIntegerField(blank=True, null=True)
    failure_count = models.PositiveIntegerField(blank=True, null=True)

    created_at = models.DateTimeField(verbose_name=_("Created At"), auto_now_add=True)

    get_import_type_display: typing.Callable

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["bulk_import", "import_type"],
                name="hulk_dataset_unique_type_per_bulk",
            ),
        ]

    def __str__(self):
        return f"HulkBulkImportDataset(bulk_import={self.bulk_import_id} type={self.get_import_type_display()})"


class HulkEntityRelationBase(models.Model):
    uuid = models.UUIDField(verbose_name="UUID", default=uuid4, unique=True)
    bulk_import = models.ForeignKey(HulkBulkImport, on_delete=models.PROTECT)
    created_at = models.DateTimeField(verbose_name=_("Created At"), auto_now_add=True)

    entity: models.OneToOneField

    entity_id: int

    class Meta:
        abstract = True

    @classmethod
    def get_entity_cls(cls):
        return cls._meta.get_field("entity").remote_field.model


class HulkAttachment(HulkEntityRelationBase):
    # OneToOneField (not FK): exports annotate ``hulk_uuid`` via the reverse
    # relation, so allowing >1 hulk row per entity would multiply export rows.
    entity = models.OneToOneField("contrib.Attachment", on_delete=models.CASCADE)

    def __str__(self):
        return f"Hulk Attachment ({self.uuid})"


class HulkSourcePreview(HulkEntityRelationBase):
    entity = models.OneToOneField("contrib.SourcePreview", on_delete=models.CASCADE)

    def __str__(self):
        return f"Hulk Source Preview ({self.uuid})"


class HulkEntry(HulkEntityRelationBase):
    entity = models.OneToOneField("entry.Entry", on_delete=models.CASCADE)

    def __str__(self):
        return f"Hulk Entry ({self.uuid})"


class HulkEvent(HulkEntityRelationBase):
    entity = models.OneToOneField("event.Event", on_delete=models.CASCADE)

    def __str__(self):
        return f"Hulk Event ({self.uuid})"


class HulkFigure(HulkEntityRelationBase):
    entity = models.OneToOneField("entry.Figure", on_delete=models.CASCADE)

    def __str__(self):
        return f"Hulk Figure ({self.uuid})"
