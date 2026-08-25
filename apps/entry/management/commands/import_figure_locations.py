from rest_framework import serializers

from apps.contrib.management.base import BaseImportCommand, EnumLookup
from apps.entry.models import FigureLocation


class FigureLocationPcodeSerializer(serializers.ModelSerializer):
    """
    The narrow slice of a figure location this importer may edit: its p-code fields.

    Deliberately not built on `FigureLocationSerializer`. That one is the app's own, nested in
    `FigureSerializer.geo_locations`, and covers the whole model — 32 fields. A serializer is
    constructed per sheet row and builds and binds a field object per field, which at a few
    milliseconds a row is more than everything else a row does put together; a p-code sheet runs to
    hundreds of thousands of rows.

    Nothing is lost by narrowing to these fields. The wide serializer's own checks are decided by
    fields absent here: `validate_lat`/`validate_lon` read the coordinates, its `update()` drops
    `geocoder_metadata`, and its `validate()` derives `country` from `country_code` only when there
    is no instance to read it from — which an update-only importer never hits. The column limits
    (`pcode` 64, `pcode_source` 256) and the p-code accuracy choices come from the model.

    Narrowing is also what keeps the sheet honest: the wide serializer exposed `lat`, `lon`,
    `display_name` and `country_code` as importable columns, so a p-code sheet could silently move
    a location.
    """

    class Meta:
        model = FigureLocation
        fields = [
            "id",
            "pcode",
            "pcode_source",
            "pcode_accuracy",
        ]


class Command(BaseImportCommand):
    help = (
        "Bulk update the p-codes of existing figure locations from an .xlsx sheet. "
        "Use --make-template to generate a blank template. "
        "This importer only updates existing rows (matched by id); it never creates."
    )

    model = FigureLocation
    update_serializer = FigureLocationPcodeSerializer
    update_only = True

    # Batched writes: FigureLocation has no pre_save/post_save receivers and no auto_now columns, so
    # bulk_update leaves nothing out. A location sheet runs to hundreds of thousands of rows, where a
    # statement per row is most of the run.
    BULK_UPDATE_BATCH_SIZE = 1000

    # pcode and pcode_source are free text, so neither needs a lookup.
    lookups = [
        EnumLookup("pcode_accuracy", FigureLocation.PCODE_ACCURACY),
    ]
