import typing
from uuid import uuid4

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from utils.fields import CachedFileField


def bulk_operation_payload(instance, filename: str) -> str:
    return f"hulk/bulk-operation/{instance.pk}/payload/{uuid4()}/{filename}"


def bulk_operation_snapshot(instance, filename: str) -> str:
    return f"hulk/bulk-operation/{instance.pk}/snapshot/{uuid4()}/{filename}"


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

    # User provided fields
    payload = CachedFileField(
        verbose_name=_("Import data snapshot"),
        upload_to=bulk_operation_payload,
        max_length=2000,
    )

    # System generated fields
    status = enum.EnumField(
        enum=HULK_BULK_IMPORT_STATUS,
        default=HULK_BULK_IMPORT_STATUS.PENDING,
    )

    # Output from operation
    success_count = models.PositiveIntegerField(blank=True, null=True)
    failure_count = models.PositiveIntegerField(blank=True, null=True)

    # TODO: is this okay?
    success_dataset = CachedFileField(
        verbose_name=_("Success data snapshot"),
        upload_to=bulk_operation_payload,
        max_length=2000,
    )
    failure_dataset = models.JSONField(default=list)

    snapshot = CachedFileField(
        verbose_name=_("Existing data snapshot"),
        blank=True,
        null=True,
        upload_to=bulk_operation_snapshot,
        max_length=2000,
    )

    # Type hints
    get_action_display: typing.Callable
    get_status_display: typing.Callable

    def __str__(self):
        return f"HulkBulkImport-{self.pk}"

    def update_status(self, status: HULK_BULK_IMPORT_STATUS, commit=True):
        # If status has changed
        if status != self.status:
            if status == self.HULK_BULK_IMPORT_STATUS.IN_PROGRESS:
                self.started_at = timezone.now()
            elif status in [
                self.HULK_BULK_IMPORT_STATUS.COMPLETED,
                self.HULK_BULK_IMPORT_STATUS.FAILED,
                self.HULK_BULK_IMPORT_STATUS.KILLED,
            ]:
                self.completed_at = timezone.now()
        self.status = status
        if commit:
            self.save(update_fields=("status",))


class HulkEntityRelationBase(models.Model):
    uuid = models.UUIDField(verbose_name="UUID", default=uuid4, unique=True)
    bulk_import = models.ForeignKey(HulkBulkImport, on_delete=models.PROTECT)
    created_at = models.DateTimeField(verbose_name=_("Created At"), auto_now_add=True)

    entity: models.ForeignKey

    entity_id: int

    class Meta:
        abstract = True

    @classmethod
    def get_entity_cls(cls):
        return cls._meta.get_field("entity").remote_field.model


class HulkAttachment(HulkEntityRelationBase):
    entity = models.ForeignKey("contrib.Attachment", on_delete=models.CASCADE)

    def __str__(self):
        return f"Hulk Attachment ({self.uuid})"


class HulkSourcePreview(HulkEntityRelationBase):
    entity = models.ForeignKey("contrib.SourcePreview", on_delete=models.CASCADE)

    def __str__(self):
        return f"Hulk Source Preview ({self.uuid})"


class HulkEntry(HulkEntityRelationBase):
    entity = models.ForeignKey("entry.Entry", on_delete=models.CASCADE)

    def __str__(self):
        return f"Hulk Entry ({self.uuid})"


class HulkEvent(HulkEntityRelationBase):
    entity = models.ForeignKey("event.Event", on_delete=models.CASCADE)

    def __str__(self):
        return f"Hulk Event ({self.uuid})"


# TODO: Do we need this? We have uuid in figure to.. but it's not unique
class HulkFigure(HulkEntityRelationBase):
    entity = models.ForeignKey("entry.Figure", on_delete=models.CASCADE)

    def __str__(self):
        return f"Hulk Figure ({self.uuid})"
