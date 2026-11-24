from apps.contrib.management.base import BaseImportCommand
from apps.event.models import Event
from apps.event.serializers import EventUpdateSerializer

_INTENSITY_COLUMNS = (
    "hazard_intensity_value",
    "hazard_intensity_unit",
    "hazard_source_name",
    "hazard_source_event_id",
    "hazard_footprint_url",
    "hazard_footprint_id",
    "hazard_footprint_geometry_type",
)


class Command(BaseImportCommand):
    help = (
        "Bulk update event hazard intensity and footprint fields from an .xlsx sheet. "
        "Use --make-template to generate a blank template."
    )

    model = Event
    update_serializer = EventUpdateSerializer
    update_only = True
    match_columns = (("event_id", "pk"),)

    def import_columns(self):
        return ["event_id", *_INTENSITY_COLUMNS]

    def column_types(self):
        types = super().column_types()
        types["event_id"] = "number"
        return types
