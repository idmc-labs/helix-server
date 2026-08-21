from apps.contrib.management.base import (
    BaseImportCommand,
    CodeLookup,
    EnumLookup,
)
from apps.country.models import Country
from apps.entry.models import FigureLocation
from apps.entry.serializers import FigureLocationSerializer


class Command(BaseImportCommand):
    help = (
        "Bulk update existing figure locations from an .xlsx sheet. "
        "Use --make-template to generate a blank template. "
        "This importer only updates existing rows (matched by id); it never creates."
    )

    model = FigureLocation
    update_serializer = FigureLocationSerializer
    update_only = True

    # uuid identifies the location across systems (hulk matches entities on it), so it is not
    # location data an operator edits. geocoder_metadata is dropped by the serializer's update(),
    # which would make its column silently do nothing. moved is figure-workflow state.
    EXTRA_EXCLUDED_FIELDS = frozenset({"uuid", "geocoder_metadata", "moved"})

    # pcode_source is free text and bounding_box is a plain list of numbers, so neither needs a
    # lookup; the enums and country_code resolve against a known set of values.
    lookups = [
        EnumLookup("accuracy", FigureLocation.ACCURACY),
        EnumLookup("identifier", FigureLocation.IDENTIFIER),
        EnumLookup("geocoder", FigureLocation.GEOCODER),
        EnumLookup("pcode_accuracy", FigureLocation.PCODE_ACCURACY),
        # The column stores an iso2. Only this importer checks it: the serializer accepts any
        # string of the right length, and the figure-level check that a location sits inside its
        # figure's country runs on FigureSerializer, which a direct location update never enters.
        CodeLookup("country_code", Country, "iso2"),
    ]
