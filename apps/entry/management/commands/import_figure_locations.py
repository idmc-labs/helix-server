from rest_framework import serializers

from apps.contrib.management.base import BaseImportCommand, EnumLookup
from apps.entry.models import FigureLocation


class FigureLocationPcodeSerializer(serializers.ModelSerializer):
    """
    The p-code slice of a figure location, kept apart from the app's `FigureLocationSerializer`.

    That one covers the whole model, and one is built per sheet row. Narrowing also keeps a p-code
    sheet from carrying `lat`, `lon` or `display_name` and moving a location by accident. None of
    the wide serializer's checks read these fields, so nothing is lost.
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

    # pcode and pcode_source are free text, so neither needs a lookup.
    lookups = [
        EnumLookup("pcode_accuracy", FigureLocation.PCODE_ACCURACY),
    ]
