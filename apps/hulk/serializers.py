from django.db import transaction
from django.utils.translation import gettext
from rest_framework import serializers

from .models import HulkBulkImport
from .tasks import process_hulk_bulk_import


class HulkBulkImportSerializer(serializers.ModelSerializer):
    class Meta:
        model = HulkBulkImport
        fields = ("payload",)

    def update(self, validated_data):
        raise serializers.ValidationError(gettext("Update not allowed"))

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        instance = super().create(validated_data)
        # TODO: is RUN_TASK_SYNC required?
        if self.context.get("RUN_TASK_SYNC", False):
            print("Running background task now....")
            process_hulk_bulk_import(instance.pk)
        else:
            transaction.on_commit(lambda: process_hulk_bulk_import.delay(instance.pk))
        return instance
