from uuid import uuid4

from django.db import transaction
from django.utils.translation import gettext
from rest_framework import serializers

from .models import HulkBulkImport, HulkBulkImportDataset
from .tasks import process_hulk_bulk_import


class HulkBulkImportDatasetCreateSerializer(serializers.Serializer):
    """One entry in the ``datasets`` list of the create-mutation input."""

    # Graphene's ``Enum.from_enum(IntegerEnum)`` delivers the *integer value*
    # to resolvers, not the enum name string. Accept the integer choices so
    # validation passes; ``create()`` translates the value back to the enum
    # member when materialising the dataset row.
    import_type = serializers.ChoiceField(
        choices=[(t.value, t.name) for t in HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE],
    )
    import_file = serializers.FileField()


class HulkBulkImportSerializer(serializers.Serializer):
    """
    Trigger a HulkBulkImport with one ``HulkBulkImportDataset`` row per
    resource type. Duplicate ``import_type`` values are rejected.
    """

    datasets = HulkBulkImportDatasetCreateSerializer(many=True)

    def validate_datasets(self, value):
        if not value:
            raise serializers.ValidationError(gettext("At least one dataset is required."))
        seen = set()
        for ds in value:
            t = ds["import_type"]
            if t in seen:
                raise serializers.ValidationError(
                    gettext("Duplicate dataset for import_type %(t)s.") % {"t": t},
                )
            seen.add(t)
        return value

    def validate(self, attrs):
        # Global lock: only one bulk import may be active at a time. Reject
        # creation if any row is still PENDING or IN_PROGRESS. Admins must
        # clear stuck rows (mark as FAILED) before a new import can be queued.
        active_statuses = (
            HulkBulkImport.HULK_BULK_IMPORT_STATUS.PENDING,
            HulkBulkImport.HULK_BULK_IMPORT_STATUS.IN_PROGRESS,
        )
        if HulkBulkImport.objects.filter(status__in=active_statuses).exists():
            raise serializers.ValidationError(
                gettext(
                    "Another hulk bulk import is already pending or in progress. "
                    "Wait for it to finish before starting a new one."
                )
            )
        return attrs

    def update(self, instance, validated_data):
        raise serializers.ValidationError(gettext("Update not allowed"))

    def create(self, validated_data):
        # NOTE: ``HulkBulkImportDataset.upload_*_file`` callables embed
        # ``instance.bulk_import_id`` and ``instance.import_type.name`` in the
        # storage key. We have to create the parent + child rows *before*
        # saving each file so those values are populated when ``upload_to``
        # fires; otherwise the keys end up containing ``hulk/bulk-operation/
        # None/datasets/None/...``.
        request = self.context["request"]
        datasets = validated_data["datasets"]

        # Pre-generate the Celery task id so it is persisted on the row before
        # the worker can pick the job up — lets admins look up AsyncResult by
        # the id stored on the bulk import.
        task_id = str(uuid4())

        with transaction.atomic():
            bulk = HulkBulkImport.objects.create(
                created_by=request.user,
                celery_task_id=task_id,
            )
            for entry in datasets:
                import_type_value = entry["import_type"]  # int value
                upload = entry["import_file"]
                ds = HulkBulkImportDataset.objects.create(
                    bulk_import=bulk,
                    import_type=int(import_type_value),
                )
                ds.import_file.save(upload.name, upload, save=True)

        if self.context.get("RUN_TASK_SYNC", False):
            process_hulk_bulk_import(bulk.pk)
        else:
            transaction.on_commit(lambda: process_hulk_bulk_import.apply_async(args=[bulk.pk], task_id=task_id))
        return bulk
