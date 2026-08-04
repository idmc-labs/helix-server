from uuid import uuid4

from django.db import connection, transaction
from django.utils.translation import gettext
from rest_framework import serializers

from .models import HulkBulkImport, HulkBulkImportDataset
from .tasks import process_hulk_bulk_import

# Statuses that count as an "active" import for the single-import global lock.
_ACTIVE_IMPORT_STATUSES = (
    HulkBulkImport.HULK_BULK_IMPORT_STATUS.PENDING,
    HulkBulkImport.HULK_BULK_IMPORT_STATUS.IN_PROGRESS,
)

# Fixed key for the transaction-scoped Postgres advisory lock that serializes
# the "is another import active?" check-then-create. Any stable arbitrary
# bigint works; 0x48554C4B is ASCII "HULK".
_ACTIVE_IMPORT_ADVISORY_LOCK_KEY = 0x48554C4B

_ACTIVE_IMPORT_ERROR = gettext(
    "Another hulk bulk import is already pending or in progress. Wait for it to finish before starting a new one."
)


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
        #
        # This is an early, best-effort check to fail fast (and avoid writing
        # the uploaded files to storage) when an import is obviously already
        # running. It is NOT concurrency-safe on its own — the authoritative
        # guard is the advisory-lock-protected re-check in ``create()``.
        if HulkBulkImport.objects.filter(status__in=_ACTIVE_IMPORT_STATUSES).exists():
            raise serializers.ValidationError(_ACTIVE_IMPORT_ERROR)
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
            # Serialize the check-then-create critical section. The ``validate()``
            # ``.exists()`` check is a classic TOCTOU race: several concurrent
            # requests can all observe "no active import" before any of them
            # creates a row, so all of them create one — violating the single
            # active-import invariant. A transaction-scoped advisory lock forces
            # concurrent triggers through here one at a time; it is released
            # automatically when this transaction commits or rolls back.
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [_ACTIVE_IMPORT_ADVISORY_LOCK_KEY])
            # Authoritative re-check, now that we hold the lock: whoever got
            # here first has already committed (or is about to) their row.
            if HulkBulkImport.objects.filter(status__in=_ACTIVE_IMPORT_STATUSES).exists():
                raise serializers.ValidationError(_ACTIVE_IMPORT_ERROR)
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
